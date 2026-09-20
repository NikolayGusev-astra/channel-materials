import json, re
p = 'Nejroseti-prishli-v-igry-bez-zreniya-kak-mody-prevrashchayut-CK3-v-nastolku-s-zhivym-masterom-09-08'
d = json.load(open('resp.json', encoding='utf-8'))
# fresh fetch
import urllib.request
req = urllib.request.Request(f'https://api.telegra.ph/getPage/{p}?return_content=true')
d = json.loads(urllib.request.urlopen(req, timeout=30).read())
r = d['result']
s = json.dumps(r['content'], ensure_ascii=False)
print('ok:', d['ok'], '| title:', r['title'])
print('a-nodes:', len(re.findall(r'"tag": "a"', s)))
for h in re.findall(r'"href": "([^"]+)"', s):
    print('  href:', h)
print('blockquote:', s.count('blockquote'), '| content len:', len(s))
print('em-dash:', s.count(chr(0x2014)), '| guil:', s.count(chr(0xab)) + s.count(chr(0xbb)))
# check the old (duplicate) minecraft block is gone
print('VPT gone:', 'Video PreTraining' not in s, '| STEVE gone:', 'STEVE' not in s)
print('part1 backlink present:', 'Nuzhna-li-modeli-zrenie' in s)
