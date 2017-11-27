# [FILES]
URLS_FILE = 'input/example_input.txt'
NORMAL_RESULT_FILE = 'output/NormalResult.csv'
ABNORMAL_RESULT_FILE = 'output/AbnormalResult.csv'
TITLE_FILE = 'output/TitleUniqueUrls.txt'

# [REGEX]
TITLE_REGEX = '(?<=<title>).*(?=<\/title>)'

# [CONCURRENT]
MAX_THREAD = 30

# [REQUEST]
TIMEOUT_SECONDE = 10

# [MISC]
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0'
