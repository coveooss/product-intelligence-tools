# External
import json

# Performs and parses Coveo REST API calls.
# Before calling any class function, you must defines the class variables
# Api._platformURL, Api._orgId and Api._token.
class Api:
    def call(endpoint, paging = False):
        if paging is False:
            return Api.__callNotPaginated(endpoint)
        return Api.__callPaginated(endpoint)
        
    def __callNotPaginated(endpoint):
        # Note that if an input to format() is not in the target string (eg endpoint does not have an {orgId} parameter)
        # then that input is safely and silently ignored.
        url = '{platformUrl}rest/'.format(platformUrl = Api._platformURL) + endpoint.format(orgId = Api._orgId)
        import requests
        response = requests.get(url, headers={'Authorization': 'Bearer {}'.format(Api._token)})
        if(response.status_code != 200):
            print('ERROR ' + str(response.status_code) + ' ' + str(response.json()['errorCode']) + ' from ' + str(url))
            return False
        return json.loads(response.text)

    # pagingStopFunc takes the current JSON response (a dict) as an input,
    #   and returns True if no more pages should be fetched.
    def __callPaginated(endpoint):
        e = endpoint + '&page='
        totalResponse = []
        currResponse = []
        currPage = 0
        while currPage == 0 or len(currResponse) > 0:
            currResponse = Api.__callNotPaginated(e + str(currPage))
            if currResponse == False:
                return False
            totalResponse.extend(currResponse)
            currPage = currPage + 1
        return totalResponse
    
