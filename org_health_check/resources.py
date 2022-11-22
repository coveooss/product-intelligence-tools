# Internal
from api import Api

# Public wrapper. This is the only function that other modules should call.
def check(rKey):
    if types[rKey] is None: # None means call all classes
        [rClass(k).check() for k, rClass in types.items() if rClass is not None]
    else:
        types[rKey](rKey).check()

# Various helpers for the private check classes.

# A message about a resource, including the resource's name and id.
from collections import namedtuple
Message = namedtuple('Message', ['name', 'id', 'reason'])

# Abstract base class for all the Check classes
class CheckResource:
    # rKey is the same string used as a key in the types global variable
    def __init__(self, rKey):
        self.rKey = rKey
    
    # Check all resources
    def check(self):
        try:
            print(self.rKey + ': Starting')
            import csvwriter
            writer = csvwriter.CsvWriter(self.rKey)
            writer.writeRow(Message._fields) # Write field names as header row
            resources = self.initialize()
            msgResCount = 0 # Count of resources that have messages
            totalResCount = len(resources)
            print(self.rKey + ': Processing ' + str(totalResCount) + ' resources', end = '')
            
            for res in resources:
                print('.', end = '', flush = True)
                msgs = self.checkOne(res)
                if msgs:
                    [writer.writeRow(m) for m in msgs]
                    msgResCount = msgResCount + 1
            
            print('\n' + self.rKey + ': ' + str(msgResCount) + ' out of ' + str(totalResCount) + ' resources have messages')
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
# Each class must be registered in the types global variable.

class CheckIpe(CheckResource):
    def initialize(self):
        # https://docs.coveo.com/en/7/api-reference/extension-api#tag/Indexing-Pipeline-Extensions/operation/getExtensionsUsingGET_9
        return Api.call('organizations/{orgId}/extensions')

    def checkOne(self, ipe):
        msgs = []
        # https://docs.coveo.com/en/7/api-reference/extension-api#tag/Indexing-Pipeline-Extensions/operation/getExtensionUsingGET_6
        ipeDetail = Api.call('organizations/{orgId}/extensions/' + str(ipe['id']))
        
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
        return Api.call('organizations/{orgId}/sources?perPage=100', True)

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
            for schedule in Api.call('organizations/{orgId}/sources/' + str(source['id']) + '/schedules'):
                if schedule['refreshType'] == 'REBUILD' and schedule['enabled']:
                    addMsg('SCHEDULED REBUILD ENABLED')
                if schedule['refreshType'] == 'FULL_REFRESH' and not schedule['enabled']:
                    addMsg('SCHEDULED RESCAN DISABLED')
                # Can’t check Refresh because it only applies for certain source types;
                # eg Confluence On-premise can Refresh only if the plugin is installed

        return msgs

# Dict of resource types
types = {
    'all'    : None, # None means all resources
    'ipe'    : CheckIpe,
    'source' : CheckSource
}