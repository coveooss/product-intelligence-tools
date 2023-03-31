'''
Functions & resources shared by various product intelligence tools.
Author: Ricky Donato (rdonato@coveo.com)
'''

# IMPORTS

import inquirer
from inquirer import errors
import requests
import json


# PROMPTS

'''
Prompts the user to give a Coveo Cloud Platform bearer token. Validates that the token is valid by listing organizations the user has access to in the organization picker.

Returns:
    token(str): The Coveo Cloud Platform bearer token that was asked for.
'''


def getToken():
    question = inquirer.Password('token',
                                 message="Enter your bearer token",
                                 validate=lambda _, token: validateToken(token))
    token = inquirer.prompt([question]).get("token")
    return token


'''
Prompts the user to give an organization ID. Validates that the organization ID is valid by comparing it to a list of organizations the user has access to.

Parameters:
    organizationIDToPlatformURLMap(dict): An organizationID:platformURL map for all regions (US, EU, AU).
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    organization(str): The organization ID that was asked for.
'''


def getOrganization(organizationIDToPlatformURLMap, token):
    question = inquirer.Text('organization ID',
                             message="Enter an organization ID",
                             validate=lambda _, organization: validateOrganization(organization, organizationIDToPlatformURLMap, token))
    organization = inquirer.prompt([question]).get("organization ID")
    return organization


def getTimeFilenameSlug():
    import datetime
    # replace() to get rid of microseconds
    return str(datetime.datetime.now().replace(microsecond = 0))


'''
Prints to console a passed dictionary of content. Can also skip.

Parameters:
    messageStart(str): The presentation of the content we might want to print (length of content and type).
    content(dict): The dictionary we want to print or save.
'''


def printOrSkip(messageStart, content):
    question = inquirer.List('printOrSkip',
                             message="{} What do you want to do with the results?".format(
                                 messageStart),
                             choices=["Skip", "Print"],
                             default="Skip")
    decision = inquirer.prompt([question]).get("printOrSkip")
    if(decision == "Print"):
        print(json.dumps(content, indent=4, sort_keys=True))


# VALIDATORS
'''
Validates that the Coveo Cloud Platform bearer token is valid by listing organizations the user has access to in the organization picker.

Parameters:
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    True(boolean): If the token is valid.
'''


def validateToken(token):
    response = requests.get("https://platform.cloud.coveo.com/rest/organizations",
                            headers={"Authorization": "Bearer {}".format(token)})
    if(response.status_code == 200):
        return True
    else:
        raise errors.ValidationError("", "Token is invalid")


'''
Validates that an organization ID is valid by comparing it to a list of organizations the user has access to.

Parameters:
    organization(str): An organization ID.
    organizationIDToPlatformURLMap(dict): An organizationID:platformURL map for all regions (US, EU, AU).
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    True(boolean): If the organization ID is valid.
'''


def validateOrganization(organization, organizationIDToPlatformURLMap, token):
    if(organization not in organizationIDToPlatformURLMap.keys()):
        raise errors.ValidationError("", "This organization does not exist")
    platformURL = organizationIDToPlatformURLMap[organization]
    return True


# API CALLS

'''
Gets organizations the user has access to in the organization picker as a map of organizationID:platformURL.

Parameters:
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    organizationIDToPlatformURLMap(dict): An organizationID:platformURL map for all regions (US, EU, AU).
'''


def getAllRegionsOrganizations(token):
    organizationIDToPlatformURLMap = {}
    organizationIDToAnalyticsURLMap = {}
    for urlSet in [("https://platform.cloud.coveo.com/", "https://analytics.cloud.coveo.com/"), ("https://platform-eu.cloud.coveo.com/", "https://analytics-eu.cloud.coveo.com/"), ("https://platform-au.cloud.coveo.com/", "https://analytics-au.cloud.coveo.com/")]:
        platformURL = urlSet[0]
        response = requests.get("{}rest/organizations".format(platformURL),
                                headers={"Authorization": "Bearer {}".format(token)})
        body = json.loads(response.text)
        for organization in body:
            organizationIDToPlatformURLMap[organization["id"]] = platformURL
            organizationIDToAnalyticsURLMap[organization["id"]] = urlSet[1]
    return organizationIDToPlatformURLMap, organizationIDToAnalyticsURLMap


# MAIN SECTIONS

'''
Runs the organization selection section, where you get a validated organization ID along with the right platform URL according to this organization's region.

Parameters:
    organizationIDToPlatformURLMap(dict): An organizationID:platformURL map for all regions (US, EU, AU).
    token(str): A Coveo Cloud Platform bearer token.

Returns:
    platformURL(str): The right Coveo Cloud URL depending on the platform region (US, EU, AU).
    organization(str): An organization ID.
'''


def organizationSelection(organizationIDToPlatformURLMap, organizationIDToAnalyticsURLMap, token):
    organization = getOrganization(organizationIDToPlatformURLMap, token)
    platformURL = organizationIDToPlatformURLMap[organization]
    uaURL = organizationIDToAnalyticsURLMap[organization]
    return platformURL, uaURL, organization


# STEPS

'''
Restarts the tool, but starting at the organization section.

Parameters:
    token(str): A Coveo Cloud Platform bearer token.
'''


def goToOrganizationSelection(token):
    organizationIDToPlatformURLMap, organizationIDToAnalyticsURLMap = getAllRegionsOrganizations(token)
    platformURL, uaURL, organization = organizationSelection(
        organizationIDToPlatformURLMap, organizationIDToAnalyticsURLMap, token)
    return platformURL, uaURL, organization


'''
Starting point of the tool.
'''


def start():
    token = getToken()
    platformURL, uaURL, organization = goToOrganizationSelection(token)
    return token, platformURL, uaURL, organization