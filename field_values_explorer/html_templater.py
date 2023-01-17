'''
This templater module will be used by the field_values_explorer script to build a HTML file for each pipeline.
'''

from datetime import datetime
import globalTools


def getHTMLTop(fileName):
    return f'''
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


def getHTMLPipeline(organization, field, maxFieldValues, isViewAllContent, pipeline):
    return f'''
    <div id="wrapper">
    <span class="label" id="orgDescription">Created: {datetime.now()}<br>
    Org: {organization}<br>
    Field: {field}<br>
    Max values: {maxFieldValues}<br>
    View all content: {isViewAllContent}<br>
    Pipeline: {pipeline}</span>
    <div class="branch lv1">
    '''


def getHTMLFieldValue(fieldValue, fieldValueCount):
    return f'''
      <div class="entry">
        <span class="label" id="pipelineContent">{fieldValue}: {fieldValueCount}</span>
      </div>
    '''


def getHTMLBottom():
    return f'''
    </div>
    </div>
    </body>
    </html>
    '''


'''
Saves to HTML file the content based on the pipelines selected.
'''


def saveToHTML(organization, field, maxFieldValues, isViewAllContent, fieldValues):
    for pipeline in fieldValues.keys():
        from pathvalidate import sanitize_filename
        fileName = sanitize_filename('fieldValues-{}-{}-{}-{}.html'.format(
            organization, field, "empty" if(pipeline == "") else pipeline, globalTools.getTimeFilenameSlug()))
        with open(fileName, 'w') as f:
            f.write(getHTMLTop(fileName))
            f.write(getHTMLPipeline(organization, field,
                                    maxFieldValues, isViewAllContent, pipeline))
            for fieldValue, fieldValueCount in fieldValues[pipeline].items():
                f.write(getHTMLFieldValue(fieldValue, fieldValueCount))
            f.write(getHTMLBottom())
