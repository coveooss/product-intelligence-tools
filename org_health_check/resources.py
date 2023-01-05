# Public wrapper around resourcesPrivate
import resourcesPrivate

# Dict of resource types
types = {
    'all'       : None, # None means all resources
    'ipe'       : resourcesPrivate.CheckIpe,
    'source'    : resourcesPrivate.CheckSource,
    'condition' : resourcesPrivate.CheckCondition
}

# rKey is the key in types
def check(rKey):
    if types[rKey] is None: # None means call all classes
        [rClass(k).check() for k, rClass in types.items() if rClass is not None]
    else:
        types[rKey](rKey).check()