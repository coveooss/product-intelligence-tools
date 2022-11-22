# Writes a CSV file. Wraps the csv.writer library. 
class CsvWriter:
    # Before instantiating this object, you must have defined the class variable CsvWriter._baseFileName.
    def __init__(self, fileNameSuffix):
        import csv
        self.fileName = CsvWriter._baseFileName + '-' + fileNameSuffix + '.csv'
        self.f = open(self.fileName, 'w', newline = '')
        self.w = csv.writer(self.f)
    def writeRow(self, row):
        self.w.writerow(row)