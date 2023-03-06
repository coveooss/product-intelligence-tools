# Public wrapper around resourcesPrivate
import resourcesPrivate

# Dict of resource types
types = {
    'ipe'       : resourcesPrivate.CheckIpe      ('ipe'),
    'source'    : resourcesPrivate.CheckSource   ('source'),
    'condition' : resourcesPrivate.CheckCondition('condition'),
    'qp'        : resourcesPrivate.CheckQp       ('qp'),
    'mlmodel'   : resourcesPrivate.CheckMlModel  ('mlmodel'),
    'field'     : resourcesPrivate.CheckField    ('field')
}

def runsQueries(rKey):
    return types[rKey].runsQueries

def needsViewAllContent(rKey):
    return types[rKey].needsViewAllContent

def check(rKey):
    return types[rKey].check()