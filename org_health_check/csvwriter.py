# Writes a CSV file. Wraps the csv.writer library. 
class CsvWriter:
    def setFolder(folderName):
        from pathvalidate import sanitize_filepath
        from pathlib import Path
        CsvWriter._folderPath = Path(sanitize_filepath(folderName))
        CsvWriter._folderPath.mkdir()

    # Before instantiating this object, you must have called the class function setFolder().
    def __init__(self, fileName):
        self.fileName = CsvWriter._folderPath / (fileName + '.csv')
        self.fileName = self.fileName.resolve()

        # Specify encoding in case output needs Unicode
        self.fileDesc = open(self.fileName, 'w', newline = '', encoding = 'utf-8')
        import csv
        self.w = csv.writer(self.fileDesc)

    def writeRow(self, row):
        self.w.writerow(row)