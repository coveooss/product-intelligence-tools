# Writes a CSV file. Wraps the csv.writer library. 
class CsvWriter:
    # Before instantiating this object, you must have defined the class variable CsvWriter._baseFileName.
    def __init__(self, fileNameSuffix):
        from pathvalidate import sanitize_filepath
        self.fileName = sanitize_filepath(CsvWriter._baseFileName + '-' + fileNameSuffix + '.csv')
        # Specify encoding in case output needs Unicode
        self.f = open(self.fileName, 'w', newline = '', encoding = 'utf-8')
        import csv
        self.w = csv.writer(self.f)
    def writeRow(self, row):
        self.w.writerow(row)