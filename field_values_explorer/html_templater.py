'''
This templater module will be used by the field_values_explorer script to build a HTML file for each pipeline.
'''

from datetime import datetime
from pathvalidate import sanitize_filename


def getHTMLTop(fileName):
    '''
    Gets the top of the HTML file that's going to be generated.

    Parameters:
        fileName(str): The name of the file that's going to be generated.

    Returns:
        htmlContent(str): HTML content we want to get.
    '''
    htmlContent = f'''
    <!DOCTYPE html>
    <html lang="en" >
    <head>
      <meta charset="UTF-8">
      <title>{fileName}</title>
      <link rel="stylesheet" href="./style.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prefixfree/1.0.7/prefixfree.min.js"></script>
    </head>
    <body>
    '''
    return htmlContent


def getHTMLPipeline(organization, field, maxFieldValues, isViewAllContent, pipeline):
    '''
    Gets the box that displays the concerned pipeline infos & context.

    Parameters:
        organization(str): An organization ID.
        field(str): A field name.
        maxFieldValues(int): The max number of field values for a pieline.
        isViewAllContent(str): true or false in string, if the user decided to enabled the viewAllContent parameter or not.
        pipeline(str): A pipeline name.

    Returns:
        htmlContent(str): HTML content we want to get.
    '''
    htmlContent = f'''
    <div id="wrapper">
    <span class="label" id="orgDescription">Created: {datetime.now()}<br>
    Org: {organization}<br>
    Field: {field}<br>
    Max values: {maxFieldValues}<br>
    View all content: {isViewAllContent}<br>
    Pipeline: {pipeline}</span>
    <div class="branch lv1">
    '''
    return htmlContent


def getHTMLFieldValue(fieldValue, fieldValueCount):
    '''
    Gets the box with the field value count for a single field value.

    Parameters:
        fieldValue(str): The name of the field value.
        fieldValueCount(str): The count of values for that field value.

    Returns:
        htmlContent(str): HTML content we want to get.
    '''
    htmlContent = f'''
      <div class="entry">
        <span class="label" id="pipelineContent">{fieldValue}: {fieldValueCount}</span>
      </div>
    '''
    return htmlContent


def getHTMLBottom():
    '''
    Gets the bottom of the HTML file that's going to be generated.

    Returns:
        htmlContent(str): HTML content we want to get.
    '''
    htmlContent = f'''
    </div>
    </div>
    </body>
    </html>
    '''
    return htmlContent


def saveToHTML(organization, field, maxFieldValues, isViewAllContent, fieldValues):
    '''
    Saves to HTML file the content based on the pipelines selected.

    Parameters:
        organization(str): An organization ID.
        field(str): A field name.
        maxFieldValues(int): The max number of field values for a pieline.
        isViewAllContent(str): true or false in string, if the user decided to enabled the viewAllContent parameter or not.
        fieldValues(dict): The dictionary containing the field values for each pipeline.
    '''
    for pipeline in fieldValues.keys():
        fileName = sanitize_filename('fieldValues-{}-{}-{}.html'.format(
            organization, field, "empty" if(pipeline == "") else pipeline))
        with open(fileName, 'w') as f:
            f.write(getHTMLTop(fileName))
            f.write(getHTMLPipeline(organization, field,
                                    maxFieldValues, isViewAllContent, pipeline))
            for fieldValue, fieldValueCount in fieldValues[pipeline].items():
                f.write(getHTMLFieldValue(fieldValue, fieldValueCount))
            f.write(getHTMLBottom())
