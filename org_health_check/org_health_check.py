# The main file that starts the application.
def start():
    import resources
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--resource', choices = (['all'] + list(resources.types.keys())), required = True, help = 'The resources to check. Note that checking certain resources requires View All Content permission or consumes a small number of QPMs.', nargs='+')
    args = parser.parse_args()
    
    # set removes duplicates, sort guarantees order
    if 'all' in args.resource: # Collect all resource types
        rToCheck = sorted(set(resources.types.keys()))
    else:
        rToCheck = sorted(set(args.resource))
        
    # Print warnings
    runsQueries = [r for r in rToCheck if resources.runsQueries(r)]
    if runsQueries:
        print('WARNING: These checks consume a small number of QPMs: ' + ', '.join(runsQueries))
    needsViewAllContent = [r for r in rToCheck if resources.needsViewAllContent(r)]
    if needsViewAllContent:
        print('WARNING: These checks require that your bearer token has Search - View All Content privilege: ' + ', '.join(needsViewAllContent))

    print() # Newline
    import globalTools
    from api import Api
    Api._token, Api._platformURL, Api._uaURL, Api._orgId = globalTools.start()
    
    from csvwriter import CsvWriter
    CsvWriter.setFolder('org_health_check-{}-{}'.format(Api().orgId, globalTools.getTimeFilenameSlug()))

    [resources.check(r) for r in rToCheck]

start()