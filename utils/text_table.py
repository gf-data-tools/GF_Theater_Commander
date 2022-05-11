import csv

SUPPORTED_IETF = ['ko-KR', 'zh-CN', 'en-US', 'ja-JP', 'zh-TW']

class TextTable():
    def __init__(self, file_path:str, lang:str='zh-CN'):
        """

        Args:
            file_path (str): path of the .tsv file
            lang (str, optional): IETF tag for default language, can be 'ko-KR', 'zh-CN', 'en-US', 'ja-JP' or 'zh-TW'. Defaults to 'zh-CN'.
        """        
        with open(file_path,'r',encoding='utf-8') as f:
            self.data = dict()
            for row in csv.DictReader(f,delimiter='\t'):
                self.data[row['key']] = row
        self.lang = lang if lang in SUPPORTED_IETF else 'zh-CN'
    
    def __call__(self, key:str, lang:str=None):
        """Get text string for given key and language

        Args:
            key (str): Key
            lang (str, optional): IETF tag for desired language. Defaults to self.lang.

        Returns:
            str: self.data[key][lang] if available, else return the original key
        """
        lang = lang if lang else self.lang
        trans = self.data.get(key)
        if trans is None or trans[lang] == '':
            return key
        return trans[lang]