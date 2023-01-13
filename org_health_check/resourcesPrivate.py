# Internal
from api import Api

# This module contains various classes that check the health of one resource type,
# eg one class that checks IPEs.

# Various helpers for the Check classes.

# A message about a resource, including the resource's name and id.
from collections import namedtuple
Message = namedtuple('Message', ['name', 'id', 'reason'])

# Abstract base class for all the Check classes
class CheckResource:
    # rKey is the same string used as a key in the types global variable
    def __init__(self, rKey, runsQueries = False, needsViewAllContent = False):
        self.rKey = rKey
        self.queryCount = None
        self.runsQueries = runsQueries
        if self.runsQueries:
            self.queryCount = 0
        self.needsViewAllContent = needsViewAllContent
    
    # Wrapper around print()
    def log(self, *args, **kwargs):
        print(str(self.rKey) + ': ', end = '')
        print(*args, **kwargs)
    
    # Run a query on search/v2?organizationId={orgId}
    # queryParams is concatenated to this call, eg "&viewAllContent=true&q=MY_DOCUMENT_TITLE"
    # Return results
    def runQuery(self, queryParams):
        if not self.runsQueries:
            self.log('ERROR: Trying to perform query when not properly intialized')
            return None
            
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Search-V2/operation/searchUsingGet
        endPt = 'search/v2?organizationId={orgId}'
        searchResults = Api.call(endPt + queryParams, 'GET')
        self.queryCount = self.queryCount + 1
        return searchResults
    
    # Check all resources
    def check(self):
        try:
            print('')
            self.log('Starting')

            import csvwriter
            writer = csvwriter.CsvWriter(self.rKey)
            writer.writeRow(Message._fields) # Write field names as header row
            resources = self.initialize()
            msgResCount = 0 # Count of resources that have messages
            totalResCount = len(resources)
            self.log('Processing ' + str(totalResCount) + ' resources', end = '')
            
            for res in resources:
                print('.', end = '', flush = True)
                msgs = self.checkOne(res)
                if msgs:
                    [writer.writeRow(m) for m in msgs]
                    msgResCount = msgResCount + 1
            print('')
            self.log(str(msgResCount) + ' out of ' + str(totalResCount) + ' resources have messages')
            if self.runsQueries:
                self.log('Consumed ' + str(self.queryCount) + ' QPMs')
        finally:
            writer.f.close()
        return True
    
    # Initialize the check, do any setup required.
    # Return seq of resources to process.
    def initialize(self):
        raise NotImplementedError

    # Check one input resource.
    # Return:
    #   a seq of Messages about that resource
    def checkOne(self, res):
        raise NotImplementedError

# Check classes
#
# Each such class checks the status of one resource type, eg IPE or source.
# Each class inherits from CheckResource and implements the abstract functions in that class.
# Each class must be registered in the resources.types global variable.

class CheckIpe(CheckResource):
    def initialize(self):
        # https://docs.coveo.com/en/7/api-reference/extension-api#tag/Indexing-Pipeline-Extensions/operation/getExtensionsUsingGET_9
        return Api.call('organizations/{orgId}/extensions', 'GET')

    def checkOne(self, ipe):
        msgs = []
        # https://docs.coveo.com/en/7/api-reference/extension-api#tag/Indexing-Pipeline-Extensions/operation/getExtensionUsingGET_6
        ipeDetail = Api.call('organizations/{orgId}/extensions/' + str(ipe['id']) ,'GET')
        
        def addMsg(s):
            return msgs.append(Message(ipeDetail['name'], ipeDetail['id'], s))
        
        if not ipeDetail['enabled']:
            addMsg('DISABLED')
        if not ipeDetail.get('usedBy') or len(ipeDetail.get('usedBy')) < 1:
            addMsg('NOT USED BY ANY SOURCE')
        if ipeDetail['status']['durationHealth']['healthIndicator'] != 'GOOD':
            addMsg('HEALTH INDICATOR: ' + str(ipeDetail['status']['durationHealth']['healthIndicator']))
        if ipeDetail['status']['timeoutHealth']['healthIndicator'] != 'GOOD':
            addMsg('TIMEOUT INDICATOR: ' + str(ipeDetail['status']['timeoutHealth']['healthIndicator']))
        if ipeDetail['status']['timeoutLikeliness'] != 'NONE':
            addMsg('TIMEOUT LIKELINESS: ' + str(ipeDetail['status']['timeoutLikeliness']))
        
        return msgs

class CheckSource(CheckResource):
    def initialize(self):
        # https://docs.coveo.com/en/15/api-reference/source-api#tag/Sources/operation/getSourcesUsingGET_6
        return Api.callPaginated('organizations/{orgId}/sources?perPage=100', 'GET')

    def checkOne(self, source):
        msgs = []

        def addMsg(s):
            msgs.append(Message(source['name'], source['id'], s))
        
        if 'configurationError' in source:
            addMsg('CONFIGURATION ERROR: ' + str(source['configurationError']['message']))
        if not source['information'].get('lastOperation'):
            addMsg('OPERATION ERROR: NO LAST OPERATION')
        elif source['information']['lastOperation'].get('result', 'ERROR') == 'ERROR':
            addMsg('OPERATION ERROR: ' + str(source['information']['lastOperation']['errorCode']))
        if source['information']['sourceStatus']['extendedCurrentStatus'] in ['DISABLED', 'ERROR', 'PAUSED_ON_ERROR', 'PAUSED', 'PAUSING']:
            addMsg('STATUS ERROR: ' + str(source['information']['sourceStatus']['extendedCurrentStatus']))
        if source['information']['numberOfDocuments'] <= 0:
            addMsg('NO DOCUMENTS')
        if source['information'].get('rebuildRequired'):
            addMsg('REBUILD REQUIRED')

        # Check schedules
        if not source['pushEnabled']: # Push sources don't have schedules
            # https://docs.coveo.com/en/15/api-reference/source-api#tag/Sources/operation/getSourceSchedulesUsingGET_6
            for schedule in Api.call('organizations/{orgId}/sources/' + str(source['id']) + '/schedules', 'GET'):
                if schedule['refreshType'] == 'REBUILD' and schedule['enabled']:
                    addMsg('SCHEDULED REBUILD ENABLED')
                if schedule['refreshType'] == 'FULL_REFRESH' and not schedule['enabled']:
                    addMsg('SCHEDULED RESCAN DISABLED')
                # Can’t check Refresh because it only applies for certain source types;
                # eg Confluence On-premise can Refresh only if the plugin is installed

        return msgs

class CheckCondition(CheckResource):
    def initialize(self):
        self.noCondition = {'definition': 'NO CONDITION', 'id': 'NO CONDITION'}
    
        # Get all query pipelines and QP statements so that later we can identify which Conditions have no QP.
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Pipelines/operation/listQueryPipelinesV1
        allQps = Api.callPaginated('search/v1/admin/pipelines?organizationId={orgId}&perPage=200', 'GET')

        # The API returns extra QPs used for A/B tests, which should be ignored.
        # These QPs have the form 'ORIGINAL_QP_NAME-mirror-SOME_NUMBER'
        self.allQps = [qp for qp in allQps if '-mirror-' not in qp['name']]

        for qp in self.allQps:
            # https://docs.coveo.com/en/13/api-reference/search-api#tag/Statements-V2/operation/listQueryPipelineStatementsV2
            qp['statements'] = Api.callPaginatedWrapped('search/v2/admin/pipelines/' + qp['id'] + '/statements?organizationId={orgId}&perPage=200', 'GET', 'statements', 'totalPages')

            # If a QP has no condition, the value is None
            if qp['condition'] == None:
                qp['condition'] = self.noCondition
            
            # If a statement has no condition, the key is undefined
            for stmt in qp['statements']:
                if 'condition' not in stmt:
                    stmt['condition'] = self.noCondition

        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Conditions/operation/listConditions
        ret = Api.callPaginatedWrapped('search/v1/admin/pipelines/statements?organizationId={orgId}&perPage=200', 'GET', 'statements', 'totalPages')
        ret.append(self.noCondition) # Add to list of conditions so we can check against it later
        return ret

    def checkOne(self, condition):
        msgs = []
        def addMsg(s):
            msgs.append(Message(condition['definition'], condition['id'], s))

        # Find the QPs that share this condition
        qpAssoc = [qp for qp in self.allQps if qp['condition']['id'] == condition['id']]

        # Find the statements that share this condition
        stmtAssoc = []
        for qp in self.allQps:
            for stmt in qp['statements']:
                if stmt['condition']['id'] == condition['id']:
                    stmt['qp'] = qp # Save the statement's QP, need this later
                    stmtAssoc.append(stmt)
        
        if len(qpAssoc) < 1 and len(stmtAssoc) < 1:
            addMsg('NOT ASSOCIATED WITH ANY QUERY PIPELINE OR STATEMENT')
        
        # Multiple pipelines should not share the same condition, unless it is No Condition
        if len(qpAssoc) > 1 and condition != self.noCondition:
            addMsg('CONFLICT: SHARED BY ' + str(len(qpAssoc)) + ' QUERY PIPELINES ' + ','.join([qp['name'] for qp in qpAssoc]))

        # Compare the statements to each other
        # Starting j at i + 1 guarantees:
        #       you never compare an item to itself
        #   and you never compare the same item twice
        for i in range(len(stmtAssoc)):
            for j in range(i + 1, len(stmtAssoc)):
                stmt = stmtAssoc[i]
                stmt2 = stmtAssoc[j]
                
                # Check for statements:
                #   in the same query pipeline
                #   AND have the same feature type (eg trigger)
                if stmt['qp'     ] == stmt2['qp'     ] and \
                   stmt['feature'] == stmt2['feature']:
                   
                    def addStmtMsg(msg):
                        addMsg(msg + ' IN QUERY PIPELINE ' + str(stmt['qp']['name']) + ': ' + str(stmt['definition']) + ', ' + str(stmt2['definition']))
                    
                    # Redirect triggers should not be paired with any other triggers
                    # Query triggers should not be paired with Redirect or Query triggers
                    if stmt['feature'] == 'trigger':
                        if   any([s['definition'].startswith('redirect') for s in [stmt, stmt2]]):
                            addStmtMsg('redirect trigger RUNS ON SAME CONDITION AS OTHER trigger')
                        elif all([s['definition'].startswith('query'   ) for s in [stmt, stmt2]]):
                            addStmtMsg('MULTIPLE query triggers')

                    # Multiple ranking weights on the same factor should not execute
                    if stmt['feature'] == 'rankingweight':
                        # stmt['definition'] has form 'rank adjacency: 5, concept: 5, docDate: 5, summary: 5, TFIDF: 7, title: 7'
                        import re
                        factors = zip(re.findall('\d+', stmt['definition']), re.findall('\d+', stmt2['definition']))
                        if any([f[0] != '5' and f[1] != '5' and f[0] != f[1] for f in factors]):
                            addStmtMsg('MULTIPLE rankingweights ON SAME FACTOR')

                    # Multiple query parameters of the same parameter name should not be overridden
                    if stmt['feature'] == 'queryParamOverride':
                        # stmt['definition'] has form 'override query lq:"ghi"'
                        def parse(s):
                            return (s['definition'].split('override query ')[1].split(':')[0],
                                    s['definition'].split(':')[1])
                            
                        s  = parse(stmt)
                        s2 = parse(stmt2)
                        # If same parameter but different value
                        if s[0] == s2[0] and s[1] != s2[1]:
                            addStmtMsg('MULTIPLE OVERRIDE PARAMETER ' + str(s[0]))

                    # OK if the statements are: filter; thesaurus; stop words; boosting; featured results
                    # Because multiples of these statements can safely execute.
                    
        return msgs