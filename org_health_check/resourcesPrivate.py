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
            self.log('Messages have been saved in ' + str(writer.fileName))
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

class CheckQp(CheckResource):
    def __init__(self, rKey):
        super().__init__(rKey, True, True) # Uses search API

    def initialize(self):
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Pipelines/operation/listQueryPipelinesV1
        return Api.callPaginated('search/v1/admin/pipelines?organizationId={orgId}&perPage=200', 'GET')

    def checkOne(self, qp):
        msgs = []
        def addMsg(s):
            msgs.append(Message(qp['name'], qp['id'], s))
            
        def buildEndpoint(part):
            return 'search/v2/admin/pipelines/' + qp['id'] + part + '?organizationId={orgId}&perPage=200'
        
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Statements-V2/operation/listQueryPipelineStatementsV2
        statements = Api.callPaginatedWrapped(buildEndpoint('/statements'), 'GET', 'statements', 'totalPages')
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
                    if searchResults is None: # Error running query
                        addMsg(str(stmt['definition']) + ': CANNOT GET SEARCH RESULTS FOR QUERY EXPRESSION')
                        continue

                    # If it used a different pipeline from the target one.
                    # Note the empty pipeline is requested as an empty string in targetQp, but returned as the string 'empty',
                    if searchResults['pipeline'] != targetQp and not (searchResults['pipeline'] == 'empty' and targetQp == ''): 
                        self.log('ERROR: search used QP "' + searchResults['pipeline'] + '" instead of target "' + targetQp + '"')
                        break
                        
                    # If no content is returned, then the QP statement is never used
                    if searchResults['totalCount'] < 1:
                        addMsg(str(stmt['definition']) + ': QUERY EXPRESSION DOES NOT MATCH ANY CONTENT IN ' + ('THE INDEX' if targetQp == '' else 'THIS QUERY PIPELINE'))
                
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Machine-learning-associations/operation/listAssociationsOfPipeline
        mlAssoc = Api.callPaginatedWrapped(buildEndpoint('/ml/model/associations'), 'GET', 'rules', 'totalPages')
        
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
        allQps = Api.callPaginated('search/v1/admin/pipelines?organizationId={orgId}&perPage=200', 'GET')
        
        # https://docs.coveo.com/en/13/api-reference/search-api#tag/Machine-learning-associations/operation/listAssociationsOfPipeline
        self.allMlAssoc = []
        [self.allMlAssoc.extend(Api.callPaginatedWrapped('search/v2/admin/pipelines/' + qp['id'] + \
            '/ml/model/associations?organizationId={orgId}&perPage=200', 'GET', 'rules', 'totalPages')) for qp in allQps]

        # https://docs.coveo.com/en/19/api-reference/machine-learning-api#tag/Machine-Learning-Models/operation/listModelsWithDetailsUsingGET_6
        return Api.call('organizations/{orgId}/machinelearning/models/details', 'GET')

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

        return msgs