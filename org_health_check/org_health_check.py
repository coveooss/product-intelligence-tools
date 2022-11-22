# The main file that starts the application.
def start():
    import resources
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--resource', choices=list(resources.types.keys()), required = True, help = 'The resources to check', nargs='+')
    args = parser.parse_args()

    import globalTools
    from api import Api
    Api._token, Api._platformURL, Api._orgId = globalTools.start()
    
    from csvwriter import CsvWriter
    CsvWriter._baseFileName = 'org_health_check-{}-{}'.format(Api._orgId, globalTools.getTimeFilenameSlug())

    [resources.check(a) for a in args.resource]

start()