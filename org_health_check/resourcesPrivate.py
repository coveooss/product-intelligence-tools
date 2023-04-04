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
    def __init__(self, runsQueries = False, needsViewAllContent = False):
        self.queryCount = None
        self.runsQueries = runsQueries
        if self.runsQueries:
            self.queryCount = 0
        self.needsViewAllContent = needsViewAllContent
    
    # Run a query on search/v2?organizationId={orgId}
    # queryParams is concatenated to this call, eg "&viewAllContent=true&q=MY_DOCUMENT_TITLE"
    # Return results
    def runQuery(self, queryParams):
        if not self.runsQueries:
            print('ERROR: Trying to perform query when not properly intialized')
            return False
            
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Search-V2/operation/searchUsingGet
        endPt = 'search/v2?organizationId={orgId}'
        searchResults = Api().call(endPt + queryParams, 'GET')
        self.queryCount = self.queryCount + 1
        return searchResults
    
    # Contact UA Read API, reading one dimension the specified number of days in the past.
    # uaFilter follows this syntax: https://docs.coveo.com/en/2727/analyze-usage-data/usage-analytics-read-filter-syntax
    # Note that spaces in uaFilter should be replaced with +, and certain characters (EG the colon : ) must be ASCII-encoded.
    def getUa(self, endpoint, dimension, numDays, uaFilter = ''):
        def getDateString(dayDelta):
            import datetime
            d = datetime.date.today() - datetime.timedelta(days = dayDelta) # Calculate delta
            timeAndTz = 'T00%3A00%3A00.000-0000' # Midnight ('%3A' is ASCII-encoded ':'), in UTC timezone
            return d.isoformat() + timeAndTz

        fromDateTime = '&from=' + getDateString(1 + numDays)
        toDateTime = '&to=' + getDateString(1) # Go to yesterday
        
        if uaFilter != '':
            uaFilter = '&f=' + uaFilter
        
        # https://docs.coveo.com/en/17/api-reference/usage-analytics-read-api#tag/Dimensions-API-Version-15/operation/get__v15_dimensions_%7Bdimension%7D_values
        return Api('ua').callPaged(endpoint + dimension + '/values?org={orgId}&n=100' + uaFilter + fromDateTime + toDateTime, 'GET', 'values', None, 'p', 1)
    
    # Utility to get all dimensions. Used for troubleshooting, not intended for production. 
    def getDimensions(self):
        # https://docs.coveo.com/en/17/api-reference/usage-analytics-read-api#tag/Dimensions-API-Version-15/operation/get__v15_dimensions
        return Api('analytics').call('dimensions?org={orgId}', 'GET')

    # Check all resources
    # rKey is the same string used as a key in the types global variable
    def check(self, rKey):
        try:
            print('')
            print('Starting ' + rKey)

            import csvwriter
            writer = csvwriter.CsvWriter(rKey)
            writer.writeRow(Message._fields) # Write field names as header row
            resources = self.initialize()
            msgResCount = 0 # Count of resources that have messages
            totalResCount = len(resources)
            print('Processing ' + str(totalResCount) + ' resources', end = '')
            
            for res in resources:
                print('.', end = '', flush = True)
                msgs = self.checkOne(res)
                if msgs:
                    [writer.writeRow(m) for m in msgs]
                    msgResCount = msgResCount + 1

            print('')
            print(str(msgResCount) + ' out of ' + str(totalResCount) + ' resources have messages')
            print('Messages have been saved in ' + str(writer.fileName))
            if self.runsQueries:
                print('Consumed ' + str(self.queryCount) + ' QPMs')
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
        return Api().call('organizations/{orgId}/extensions', 'GET')

    def checkOne(self, ipe):
        msgs = []
        # https://docs.coveo.com/en/7/api-reference/extension-api#tag/Indexing-Pipeline-Extensions/operation/getExtensionUsingGET_6
        ipeDetail = Api().call('organizations/{orgId}/extensions/' + str(ipe['id']), 'GET')

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
        avgDuration = ipeDetail['status']['dailyStatistics']['averageDurationInSeconds']
        if type(avgDuration) == float and avgDuration > 0.2:
            addMsg('AVERAGE TIMEOUT HIGH: ' + str(avgDuration))
        
        # Check if IPE script body modifies item permissions
        #
        # https://docs.coveo.com/en/34/index-content/document-object-python-api-reference
        permissionsFuncs = ['clear_permissions', 'add_allowed', 'add_denied', 'set_permissions']
        if any([p in ipeDetail['content'] for p in permissionsFuncs]):
            addMsg('IPE MODIFIES PERMISSIONS. VALIDATE IT COVERS EVERY USE CASE, AND REJECTS DOCUMENTS ON ERROR.')
        
        return msgs

class CheckSource(CheckResource):
    def initialize(self):
        # https://docs.coveo.com/en/15/api-reference/source-api#tag/Sources/operation/getSourcesUsingGET_6
        return Api().callPaged('organizations/{orgId}/sources?perPage=100', 'GET')

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
            schedules = Api().call('organizations/{orgId}/sources/'+ str(source['id']) + '/schedules', 'GET')
            
            # schedules could be empty if a schedule was never set
            if not schedules or \
              not any([s['refreshType'] == 'FULL_REFRESH' and s['enabled'] for s in schedules]): 
                addMsg('SCHEDULED RESCAN DISABLED')
            if any([s['refreshType'] == 'REBUILD' and s['enabled'] for s in schedules]):
                addMsg('SCHEDULED REBUILD ENABLED')
            # Can’t check Refresh because it only applies for certain source types;
            # eg Confluence On-premise can Refresh only if the plugin is installed

        # Check if source is unsecured for connectors that can be secured
        if source['sourceVisibility'] == 'SHARED':
          # Fully secured connectors
          securedConnectors = ['BOX', 'BOX_ENTERPRISE', 'BOX_ENTERPRISE2', 'DATABASE', 'DROPBOX', 'DROPBOX_FOR_BUSINESS', 'FILE', 'GENERIC_REST', 'GMAIL', 'GMAIL_DOMAIN_WIDE', 'GOOGLE_DRIVE_DOMAIN_WIDE', 'KHOROS', 'LITHIUM', 'MICROSOFT_DYNAMICS', 'SALESFORCE', 'SERVICENOW', 'SHAREPOINT', 'SHAREPOINT_ONLINE', 'SHAREPOINT_ONLINE2', 'SITECORE', 'SLACK', 'TEMPLATED_GENERIC_REST', 'ZENDESK']
          
          # Secured if certain things are true on the source system (eg Confluence plugin installed)
          partlySecuredConnectors = ['CATALOG', 'CONFLUENCE', 'CONFLUENCE2', 'CONFLUENCE2_HOSTED', 'JIRA2', 'JIRA2_HOSTED', 'JIVE_HOSTED', 'PUSH']
          
          if source['sourceType'] in securedConnectors or \
             source['sourceType'] in partlySecuredConnectors:
              addMsg('CONTENT PERMISSIONS NOT INDEXED')

        # Check if no web scraping for Web/Sitemap sources
        if source['sourceType'] in ['SITEMAP', 'WEB2']:
            # https://docs.coveo.com/en/15/api-reference/source-api#tag/Sources/operation/getRawSourceUsingGET_9
            rawSource = Api().call('organizations/{orgId}/sources/' + str(source['id']) + '/raw', 'GET')

            scraping = rawSource['configuration']['parameters'].get('ScrapingConfiguration')
            # Remove all whitespace from scraping
            if scraping is None or ''.join(scraping.get('value', '').split()) in ['', '[]']:
                addMsg('WEB SCRAPING DISABLED')

        return msgs

class CheckCondition(CheckResource):
    def initialize(self):
        self.noCondition = {'definition': 'NO CONDITION', 'id': 'NO CONDITION'}
    
        # Get all query pipelines and QP statements so that later we can identify which Conditions have no QP.
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Pipelines/operation/listQueryPipelinesV1
        allQps = Api().callPaged('search/v1/admin/pipelines?organizationId={orgId}&perPage=200', 'GET')

        # The API returns extra QPs used for A/B tests, which should be ignored.
        # These QPs have the form 'ORIGINAL_QP_NAME-mirror-SOME_NUMBER'
        self.allQps = [qp for qp in allQps if '-mirror-' not in qp['name']]

        for qp in self.allQps:
            # https://docs.coveo.com/en/13/api-reference/search-api#tag/Statements-V2/operation/listQueryPipelineStatementsV2
            qp['statements'] = Api().callPaged('search/v2/admin/pipelines/' + qp['id'] + '/statements?organizationId={orgId}&perPage=200', 'GET', 'statements', 'totalPages')

            # If a QP has no condition, the value is None
            if qp['condition'] == None:
                qp['condition'] = self.noCondition
            
            # If a statement has no condition, the key is undefined
            for stmt in qp['statements']:
                if 'condition' not in stmt:
                    stmt['condition'] = self.noCondition

        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Conditions/operation/listConditions
        ret = Api().callPaged('search/v1/admin/pipelines/statements?organizationId={orgId}&perPage=200', 'GET', 'statements', 'totalPages')
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
                        # stmt['definition'] has form:
                        # EITHER 'override query lq:"ghi"'
                        # OR     'override querySuggest enableWordCompletion: true'
                        def parse(s):
                            return (s['definition'].split(':')[0].split('override ')[1],
                                    s['definition'].split(':')[1])
                            
                        s  = parse(stmt)
                        s2 = parse(stmt2)
                        # If same parameter but different value
                        if s[0] == s2[0] and s[1] != s2[1]:
                            addStmtMsg('MULTIPLE OVERRIDE PARAMETER')

                    # OK if the statements are: filter; thesaurus; stop words; boosting; featured results
                    # Because multiples of these statements can safely execute.
                    
        return msgs

class CheckQp(CheckResource):
    def __init__(self):
        super().__init__(True, True) # Uses search API

    def initialize(self):
        self.numDaysChecked = 60
        
        # Get UA for query pipelines
        qpWithUa = self.getUa('dimensions/', 'SEARCHES.QUERYPIPELINE', self.numDaysChecked)

        # qpWithUa has form {'OccurrenceCount': 1, 'SEARCHES.QUERYPIPELINE': QP_NAME}
        for qp in qpWithUa:
            if qp['OccurrenceCount'] <= 0: # Should always be > 0
                raise ValueError(str(qp))
        
        self.qpWithUa = [qp['SEARCHES.QUERYPIPELINE'] for qp in qpWithUa] # Only need the QP name

        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Pipelines/operation/listQueryPipelinesV1
        return Api().callPaged('search/v1/admin/pipelines?organizationId={orgId}&perPage=200', 'GET')

    def checkOne(self, qp):
        msgs = []
        def addMsg(s):
            msgs.append(Message(qp['name'], qp['id'], s))
            
        # This QP has no recent UA. This identifies unused QPs and associated conditions, hosted search pages and statements.
        if qp['name'] not in self.qpWithUa:
            addMsg('NOT USED FOR AT LEAST ' + str(self.numDaysChecked) + ' DAYS.')
        
        def buildEndpoint(part):
            return 'search/v2/admin/pipelines/' + qp['id'] + part + '?organizationId={orgId}&perPage=200'
        
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Statements-V2/operation/listQueryPipelineStatementsV2
        statements = Api().callPaged(buildEndpoint('/statements'), 'GET', 'statements', 'totalPages')
        for stmt in statements:
            # Each statement has an id but it's not easily visible on the Admin Console,
            # so it's not pushed into the csv. Instead, use the definition.
            # Sometimes the definition has newlines, remove those.
            stmt['definition'] = stmt['definition'].replace('\n', ' ')
            
            if 'warnings' in stmt:
                [addMsg(str(stmt['definition']) + ': ' + str(w)) for w in stmt['warnings']]

            # Check each query expressions in a filter, ranking rule, or featured result
            # to see if the query expression matches any content (else the rule is useless)
            if stmt['feature'] in ['filter', 'ranking', 'top']:
                # stmt['definition'] has these forms:
                #   filter aq `@source=="Public Content"`
                #   boost `@title/="^.*Coveo.*$"` by 10
                #   top `@urihash==7Vf6bWsytplARQu3`, `@title=="Top - Query Pipeline Feature"`
                
                # Extract the query expression(s) that are wrapped in backticks
                # which is every odd-numbered item after split()
                queryExpSeq = []
                i = 0
                for exp in stmt['definition'].split('`'):
                    if i % 2 == 1:
                        queryExpSeq.append(exp)
                    i = i + 1

                # For Ranking rules and Featured Results, run on the current query pipeline.
                #
                # For filters, the ideal way to do this is too complex.
                # It requires checking if it affects the current pipeline;
                # which requires creating a new pipeline identical to the current one
                # but without the current query expression.
                # Instead, run on the empty query pipeline to see if it matches anything in the index.
                targetQp = '' # Empty QP for filters
                if stmt['feature'] != 'filter':
                    targetQp = qp['name']
                
                for exp in queryExpSeq: # run a query on every query expression found
                    # Pass query expression as q
                    queryParams = '&pipeline=' + targetQp + '&viewAllContent=true&q=' + exp
                    searchResults = self.runQuery(queryParams)
                    if searchResults is False: # Error running query
                        addMsg(str(stmt['definition']) + ': CANNOT GET SEARCH RESULTS FOR QUERY EXPRESSION')
                        continue

                    # If it used a different pipeline from the target one.
                    # Note the empty pipeline is requested as an empty string in targetQp, but returned as the string 'empty',
                    if searchResults['pipeline'] != targetQp and not (searchResults['pipeline'] == 'empty' and targetQp == ''): 
                        print('ERROR: search used QP "' + searchResults['pipeline'] + '" instead of target "' + targetQp + '"')
                        break
                        
                    # If no content is returned, then the QP statement is never used
                    if searchResults['totalCount'] < 1:
                        addMsg(str(stmt['definition']) + ': QUERY EXPRESSION DOES NOT MATCH ANY CONTENT IN ' + ('THE INDEX' if targetQp == '' else 'THIS QUERY PIPELINE'))
                
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Machine-learning-associations/operation/listAssociationsOfPipeline
        mlAssoc = Api().callPaged(buildEndpoint('/ml/model/associations'), 'GET', 'rules', 'totalPages')
        
        if len(mlAssoc) < 1: # no ML models on this QP
            addMsg('NO ML MODELS')

        for i in range(len(mlAssoc)):
            ml = mlAssoc[i]
            def addMlMsg(s):
                addMsg('MODEL ' + ml['modelDisplayName'] + ' ' + s)

            mlType = ml['modelEngine']

            if mlType not in ['topclicks', 'querysuggest', 'eventrecommendation', 'facetsense', 'mlquestionanswering']:
                addMlMsg('HAS UNRECOGNIZED ML TYPE ' + ml['modelEngine'])
                
            if mlType == 'topclicks': # ART
                if ml['rankingModifier'] > 250:
                    addMlMsg('RANKING MODIFIER ' + str(ml['rankingModifier']) + ' ABOVE RECOMMENDED VALUE')
                if ml['maxRecommendations'] > 5:
                    addMlMsg('MAX RECOMMENDATIONS ' + str(ml['maxRecommendations']) + ' ABOVE RECOMMENDED VALUE')
                # ART model structure: {'id': '67135f5b-99c2-426a-b72a-141384d301ff', 'position': 5, 'modelId': 'coveosalesforcetestakshatha_topclicks_f92ca3c4_ade9_4ab2_b5a5_406b5f6ca69b', 'modelDisplayName': 'Trailhead', 'modelEngine': 'topclicks', 'modelStatus': 'ONLINE', 'rankingModifier': 250, 'maxRecommendations': 5, 'cacheMaximumAge': 'PT10S', 'intelligentTermDetection': False, 'matchBasicExpression': False, 'matchAdvancedExpression': True, 'useAdvancedConfiguration': False}
                
            if mlType == 'querysuggest': # QS
                if ml['maxRecommendations'] > 10:
                    addMlMsg('MAX RECOMMENDATIONS ' + str(ml['maxRecommendations']) + ' ABOVE RECOMMENDED VALUE')
                # QS model structure: {'id': 'ad11402c-2056-439d-a973-a51f33553683', 'position': 7, 'modelId': 'coveosalesforcetestakshatha_querysuggest_generated_4a7148a8dd94fb4d209827db709fa662', 'modelDisplayName': 'Help Portal Query Suggest Model', 'modelEngine': 'querysuggest', 'modelStatus': 'ONLINE', 'maxRecommendations': 10, 'cacheMaximumAge': 'PT10S', 'useAdvancedConfiguration': False}
                
            if mlType == 'eventrecommendation': # CR
                if ml['rankingModifier'] > 1000:
                    addMlMsg('RANKING MODIFIER ' + str(ml['rankingModifier']) + ' ABOVE RECOMMENDED VALUE')
                # CR model structure: {'id': 'bb0cb349-c5fe-4e33-a772-073620db3921', 'position': 4, 'modelId': 'coveosalesforcetestakshatha_eventrecommendation_generated_f26da950084f91411f2487f6cd0b983f', 'modelDisplayName': 'Model11', 'modelEngine': 'eventrecommendation', 'modelStatus': 'ONLINE', 'rankingModifier': 1000, 'cacheMaximumAge': 'PT10S', 'exclusive': True, 'customQueryParameters': {}, 'description': '1 Day - For Testing Pageviews'}
                
            if mlType == 'facetsense': # DNE
                if ml['rankingModifier'] > 50:
                    addMlMsg('RANKING MODIFIER ' + str(ml['rankingModifier']) + ' ABOVE RECOMMENDED VALUE')
                # DNE model structure: {'id': '3a811bd2-65fc-4f62-a485-f103db4b677a', 'position': 2, 'modelId': 'coveosalesforcetestakshatha_facetsense_3336f122_a2ef_4694_904f_9c185d9aed31', 'modelDisplayName': 'PBM Marketplace Search DNE', 'modelEngine': 'facetsense', 'modelStatus': 'ONLINE', 'rankingModifier': 50, 'cacheMaximumAge': 'PT10S', 'customQueryParameters': {'facetOrdering': {'isEnabled': True}, 'facetValueOrdering': {'isEnabled': True}, 'facetAutoSelect': {'isEnabled': False}, 'rankingBoost': {'isEnabled': True}}, 'useAdvancedConfiguration': False}
                
            if mlType == 'mlquestionanswering': # Smart snippets
                pass # Nothing to do
                # Smart snippets model structure {'id': 'bcf5f242-f227-43c0-9061-f6f55a0648f5', 'position': 9, 'modelId': 'coveosalesforcetestakshatha_mlquestionanswering_aef64b4c_35ef_4e12_a868_4306b7f09109', 'modelDisplayName': 'Documentation - R&D - 03/01/22', 'modelEngine': 'mlquestionanswering', 'modelStatus': 'ONLINE', 'cacheMaximumAge': 'PT10S', 'contentIdKeys': ['permanentid', 'urihash']}

            # Compare the models to each other
            # Starting j at i + 1 guarantees:
            #       you never compare an item to itself
            #   and you never compare the same item twice
            for j in range(i + 1, len(mlAssoc)):
                ml2 = mlAssoc[j]

                # 2 models of the same type in the same query pipeline with the same condition or no condition
                if mlType == ml2['modelEngine'] and \
                   ml.get('condition', 'NO CONDITION') == ml2.get('condition', 'NO CONDITION'):
                    addMlMsg('RUNS ON SAME CONDITION AS OTHER mlmodel ' + str(ml2['modelDisplayName']))

        return msgs
        
class CheckMlModel(CheckResource):
    def initialize(self):
        # Get all query pipelines so that later we can identify which ml models have no QP.
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Pipelines/operation/listQueryPipelinesV1
        allQps = Api().callPaged('search/v1/admin/pipelines?organizationId={orgId}&perPage=200', 'GET')
        
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Machine-learning-associations/operation/listAssociationsOfPipeline
        self.allMlAssoc = []
        [self.allMlAssoc.extend(Api().callPaged('search/v2/admin/pipelines/' + qp['id'] + \
            '/ml/model/associations?organizationId={orgId}&perPage=200', 'GET', 'rules', 'totalPages')) for qp in allQps]

        # https://docs.coveo.com/en/19/api-reference/machine-learning-api#tag/Machine-Learning-Models/operation/listModelsWithDetailsUsingGET_6
        return Api().call('organizations/{orgId}/machinelearning/models/details', 'GET')

    def checkOne(self, mlModel):
        msgs = []
        def addMsg(s):
            msgs.append(Message(mlModel['modelDisplayName'], mlModel['id'], s))

        if mlModel.get('modelActivenessState') == 'INACTIVE':
            addMsg('INACTIVE')
        if type(mlModel['nextModelUpdateTime']) != int or mlModel['nextModelUpdateTime'] < 0:
            addMsg('INVALID NEXT UPDATE TIME')
        if any([badStatus in mlModel['status'] for badStatus in ['DEGRADED', 'FAILED', 'ERROR', 'OFFLINE']]):
            addMsg('STATUS: ' + mlModel['status'])

        for e in mlModel['modelErrorDescription']['customer_errors']:
            addMsg('ERROR: code: "' + str(e['errorCode']) + '", type "' + str(e['errorType']) + '", description "' + str(e['description']) + '"')
        
        if all([mlModel['id'] != ml['modelId'] for ml in self.allMlAssoc]):
            addMsg('NOT ASSOCIATED WITH ANY QUERY PIPELINE')
        
        if mlModel.get('extraConfig', {}).get('filterFields') == []:
            addMsg('NO FILTER FIELDS')

        # DNE or ART
        if mlModel['engineId'] in ['facetsense', 'topclicks'] and \
           mlModel['modelSizeStatistic'] < 100:
            addMsg('POOR QUERY COUNT ' + str(mlModel['modelSizeStatistic']))

        # CR
        if mlModel['engineId'] == 'eventrecommendation' and \
           mlModel['modelSizeStatistic'] < 100:
            addMsg('POOR RECOMMENDATION COUNT ' + str(mlModel['modelSizeStatistic']))

        if mlModel['engineId'] == 'querysuggest' and \
           mlModel['modelSizeStatistic'] < 100:
            addMsg('POOR CANDIDATE COUNT ' + str(mlModel['modelSizeStatistic']))

        # Smart Snippets
        count = mlModel['info'].get('preparationStats', {}).get('snippetCount', -1)
        if mlModel['engineId'] == 'mlquestionanswering' and count < 100:
            addMsg('POOR SNIPPET COUNT ' + str(count))

        # Case Classification
        if mlModel['engineId'] == 'caseclassification':
            for field, stats in mlModel['info']['trainingDetails']['performanceDetails'].items():
                if stats['hit1'] < 0.5: # Top prediction is correct
                    addMsg('FOR FIELD ' + field + ', POOR TOP 1 PREDICTION ' + str(100*stats['hit1']) + '%')
                if stats['hit3'] < 0.75: # Correct prediction in top 3
                    addMsg('FOR FIELD ' + field + ', POOR TOP 3 PREDICTION ' + str(100*stats['hit3']) + '%')

        return msgs

class CheckField(CheckResource):
    def __init__(self):
        super().__init__(True, True) # Uses search API

    def initialize(self):
        self.numDaysChecked = 60
        # https://docs.coveo.com/en/17/api-reference/usage-analytics-read-api#tag/Dimensions-API-Version-15/operation/get__v15_dimensions_custom_%7Bdimension%7D_values
        facetUa = self.getUa('dimensions/custom/', 'c_facetid', self.numDaysChecked, "(c_facetid!=''%20AND%20c_facetid!=null)")
        self.fieldsWithUa = []
        
        # facetUa has form {'OccurrenceCount': 1, 'c_facetid': FIELD_NAME}.
        for f in facetUa:
            if f['OccurrenceCount'] <= 0: # Should always be > 0
                raise ValueError(str(f))

            name = f['c_facetid'] # Only need the field name
            if not name.startswith('@'):
                name = '@' + name # Normalize the field name

            import re
            # The field name will be duplicated if it had multiple values. Remove the duplicates.
            # Duplicates end with _ and a number eg '@docsfeatureimpact_26'
            if not re.search(r'_\d+$', name): # Keep only the first one
               self.fieldsWithUa.append(name)

        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Search-V2/operation/fields
        return Api().call('search/v2/fields?organizationId={orgId}&viewAllContent=true', 'GET')['fields']
        
    def checkOne(self, field):
        msgs = []
        name = str(field['name'])
        
    # The type returned by the API is different from the type in the admin console
        typeMap = { # Key is the API type, value is the admin console type
            'Date': 'Date',
            'Double': 'Decimal',
            'LargeString': 'String',
            'Long': 'Integer 32',
            'Long64': 'Integer 64'
        }
        fType = typeMap.get(field['fieldType'], field['fieldType'])
        
        def addMsg(s):
            msgs.append(Message(name, fType, s))

        # See if field has no values in the index, using the empty pipeline.
        # Pass field name (with @) as q. You can't use /search/v2/facet because that requires the
        # field to be Facet, so instead run a query.
        queryParams = '&pipeline=&viewAllContent=true&q=' + name
        searchResults = self.runQuery(queryParams)
        if searchResults is False: # Error running query
            addMsg('CANNOT GET SEARCH RESULTS FOR FIELD')
        elif searchResults['totalCount'] < 1:
            addMsg('FIELD HAS NO VALUE IN THE INDEX')
        else: # Field has values so check if its settings are reasonable
            # Free-Text Searchable
            if field['includeInQuery']:
                addMsg('Free-Text Searchable: Impacts relevance and query performance. Does the user expect Coveo to search this field for typed keywords? If yes AND the field has many values (more than 50), it should be Free-Text Searchable. If yes BUT the field has less than 50 values, it may be better as a Facet. If no, it should be neither.')

            # Displayable in Results
            if field['includeInResults']:
                addMsg('Displayable in Results: Security risk. Ensure that this field does not contain sensitive data.')

            # Integer 32, Integer 64, Decimal, and Date are always Facet and Sortable
            if field['sortByField'] and fType not in ['Integer 32', 'Integer 64', 'Decimal', 'Date']:
                addMsg('Sortable impacts caching and can reduce query performance. If this setting is not needed, remove it.')

            # Field is (Facet or Multivalue Facet) but has no facet UA
            if ((field['groupByField'] and fType not in ['Integer 32', 'Integer 64', 'Decimal', 'Date']) or \
              field['splitGroupByField']) and \
              name not in self.fieldsWithUa:
                addMsg('Facet but not used as facet for at least ' + str(self.numDaysChecked) + ' days. Remove this setting to improve caching and query performance.')

        return msgs