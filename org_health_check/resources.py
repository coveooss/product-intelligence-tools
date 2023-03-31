# Public wrapper around resourcesPrivate
import resourcesPrivate

# Dict of resource types
types = {
    'ipe'       : resourcesPrivate.CheckIpe      (),
    'source'    : resourcesPrivate.CheckSource   (),
    'condition' : resourcesPrivate.CheckCondition(),
    'qp'        : resourcesPrivate.CheckQp       (),
    'mlmodel'   : resourcesPrivate.CheckMlModel  (),
    'field'     : resourcesPrivate.CheckField    ()
}

def runsQueries(rKey):
    return types[rKey].runsQueries

def needsViewAllContent(rKey):
    return types[rKey].needsViewAllContent

def check(rKey):
    return types[rKey].check(rKey)