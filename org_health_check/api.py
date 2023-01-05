# External
import json

# Performs and parses Coveo REST API calls.
# Before calling any class function, you must defines the class variables
# Api._platformURL, Api._orgId and Api._token.
class Api:
    def call(endpoint, contentType = None, postData = None):
        # Note that if an input to format() is not in the target string (eg endpoint does not have an {orgId} parameter)
        # then that input is safely and silently ignored.
        url = '{platformUrl}rest/'.format(platformUrl = Api._platformURL) + endpoint.format(orgId = Api._orgId)
        header = {'Authorization': 'Bearer {}'.format(Api._token)}
        if contentType is not None:
            header['Content-Type'] = contentType
        import requests
        if postData is None:
            response = requests.get( url,
              headers = header
            )
        else:
            response = requests.post(url,
              headers = header,
              data = postData
            )
        if(response.status_code != 200):
            print('ERROR ' + str(response.status_code) + ' ' + str(response.json().get('errorCode', 'no errorCode')) + ' from ' + str(url))
            return False
        return json.loads(response.text)

    def callPaginated(endpoint):
        e = endpoint + '&page='
        totalResponse = []
        currResponse = []
        currPage = 0
        while currPage == 0 or len(currResponse) > 0:
            currResponse = Api.call(e + str(currPage))
            if currResponse == False:
                return False
            totalResponse.extend(currResponse)
            currPage = currPage + 1
        return totalResponse
    
    # This function is for endpoints that wrap the paginated array in a dict.
    #   arrayKey is the key of the returned array.
    #   pageCountKey is the key of the total number of pages.
    def callPaginatedArray(endpoint, arrayKey, pageCountKey):
        e = endpoint + '&page='
        totalResponse = []
        currResponse = {arrayKey: [], pageCountKey: 1}
        currPage = 0
        while currPage < currResponse[pageCountKey]:
            currResponse = Api.call(e + str(currPage))
            if currResponse == False:
                return False
            totalResponse.extend(currResponse[arrayKey])
            currPage = currPage + 1
        return totalResponse
        
