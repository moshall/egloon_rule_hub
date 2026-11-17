"""Convert public rule sources to Loon; never reads private user profiles or subscriptions."""
from pathlib import Path
import concurrent.futures
import hashlib
import ipaddress
import json
import urllib.request
import yaml

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'Rule/Loon/OnlineCompat'
SOURCES = {
    'openai_lsr': 'https://raw.githubusercontent.com/moshall/egloon_rule_hub/main/Rule/Loon/OpenAI/OpenAI.lsr',
    'netflix_lsr': 'https://raw.githubusercontent.com/moshall/egloon_rule_hub/main/Rule/Loon/Netflix/Netflix.lsr',
    'pico': 'https://gist.githubusercontent.com/moshall/bdcaaca288bad5adfe5d2c9a926de873/raw/79f842b8eda7bec3b26a923790992c120b695f2d/picopi_inner_rule_set.yaml',
    'lan': 'https://raw.githubusercontent.com/Repcz/Tool/refs/heads/X/Egern/Rules/Lan.yaml',
    'direct': 'https://raw.githubusercontent.com/GMOogway/shadowrocket-rules/master/sr_direct_list.module',
    'china_dns': 'https://raw.githubusercontent.com/Repcz/EgernRules/refs/heads/X/Rules/China/China_All.yaml',
    'global_dns': 'https://raw.githubusercontent.com/Repcz/EgernRules/refs/heads/X/Rules/Global/Global_All.yaml',
}
FIELDS = {'domain_set':'DOMAIN','domain_suffix_set':'DOMAIN-SUFFIX',
          'domain_keyword_set':'DOMAIN-KEYWORD','ip_cidr_set':'IP-CIDR','ip_cidr6_set':'IP-CIDR6'}

def fetch(item):
    name,url=item
    req=urllib.request.Request(url,headers={'User-Agent':'Loon-public-rule-converter'})
    with urllib.request.urlopen(req,timeout=45) as r:return name,r.read().decode('utf-8-sig')

def egern_rules(text):
    data=yaml.safe_load(text);rows=[]
    for key,values in data.items():
        if key not in FIELDS:raise ValueError('Unsupported rule field: '+key)
        for value in values:
            typ=FIELDS[key]
            if typ.startswith('IP-CIDR'):
                typ='IP-CIDR6' if ipaddress.ip_network(value,strict=False).version==6 else 'IP-CIDR'
            rows.append(f'{typ},{value}')
    assert rows
    return list(dict.fromkeys(rows))

def sr_rules(text):
    rows=[];inside=False
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith(('#',';')):continue
        if line.startswith('['):inside=line.lower()=='[rule]';continue
        if not inside:continue
        typ=line.split(',',1)[0]
        if typ not in {'DOMAIN','DOMAIN-SUFFIX','DOMAIN-KEYWORD','URL-REGEX','IP-CIDR','IP-CIDR6','GEOIP','IP-ASN'}:
            raise ValueError('Unsupported SR rule: '+typ)
        condition,policy=line.rsplit(',',1)
        assert policy.strip()=='DIRECT'
        # SR wraps URL regexes in quotes; Loon rule syntax uses the expression itself.
        if typ=='URL-REGEX':condition=typ+','+condition.split(',',1)[1].strip('"')
        rows.append(condition)
    assert rows
    return list(dict.fromkeys(rows))

def dns_maps(text,server,mappings):
    data=yaml.safe_load(text);skipped={}
    for key,values in data.items():
        if key not in {'domain_set','domain_suffix_set'}:
            skipped[key]=len(values) if isinstance(values,list) else 1
            continue
        for domain in values:
            assert isinstance(domain,str) and not any(c in domain for c in '\n\r=,')
            mappings.setdefault(domain,server)
            if key=='domain_suffix_set':mappings.setdefault('*.'+domain,server)
    return skipped

def build():
    with concurrent.futures.ThreadPoolExecutor(5) as pool:sources=dict(pool.map(fetch,SOURCES.items()))
    rules={'pico.lsr':egern_rules(sources['pico']), 'lan.lsr':egern_rules(sources['lan']),
           'direct.lsr':sr_rules(sources['direct']), 'cn.lsr':['GEOIP,CN']}
    skipped_route_regex = {}
    for name in ('openai', 'netflix'):
        rows=[];excluded=[]
        for raw in sources[name+'_lsr'].splitlines():
            line=raw.strip()
            if not line or line.startswith('#'):continue
            if line.startswith('DOMAIN-REGEX,'):excluded.append(line);continue
            assert line.split(',',1)[0] in {'DOMAIN','DOMAIN-SUFFIX','DOMAIN-KEYWORD','IP-CIDR','IP-CIDR6','IP-ASN','USER-AGENT'}
            rows.append(line)
        assert rows
        rules[name+'.lsr']=rows
        skipped_route_regex[name]=excluded
    # Preserve precedence for identical host patterns; wildcard specificity remains Loon's own behavior.
    mappings={}
    for name in ('home','lan','local'):
        mappings[name]='system';mappings['*.'+name]='system'
    skipped={'China':dns_maps(sources['china_dns'],'https://223.5.5.5/dns-query',mappings)}
    mappings.setdefault('*.icloud.com','https://223.5.5.5/dns-query')
    mappings.setdefault('*.goog','https://dns.google/dns-query')
    skipped['Global']=dns_maps(sources['global_dns'],'https://dns.google/dns-query',mappings)
    plugin=['#!name = Egern DNS 分类映射（Loon兼容）',
            '#!desc = 国内使用阿里DoH，国外使用Google DoH。仅域名和后缀；关键词无法等价迁移。每类固定单上游，非Egern多上游池。',
            '#!author = moshall',
            '# 原始源及转换差异见 manifest.json；不设置DNS代理出口，不包含脚本与证书。', '[Host]']
    plugin += [f'{domain} = server:{server}' for domain,server in mappings.items()]
    contents={n:'# Public source converted to Loon; no proxy credentials.\n'+'\n'.join(rows)+'\n' for n,rows in rules.items()}
    contents['dns_mapping.lpx']='\n'.join(plugin)+'\n'
    metadata={'sources':SOURCES,'counts':{n:len(rows) for n,rows in rules.items()},'dns_host_mappings':len(mappings),
              'dns_skipped':skipped,'unsupported_domain_regex':skipped_route_regex,'dns_limitations':['Only domain and suffix conditions converted; keywords and regexes not approximated.',
              'Host specificity and matching order follow Loon, not Egern forward first-match.',
              'One fixed DoH per category replaces the Egern upstream pools.',
              'Does not configure or guarantee a proxy egress for encrypted DNS.'],
              'sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in contents.items()}}
    contents['manifest.json']=json.dumps(metadata,ensure_ascii=False,indent=2)+'\n'
    assert not any('target=Egern' in t or 'private-key=' in t or 'sub.mypresident' in t for t in contents.values())
    # Fetch/convert all sources successfully before replacing any outputs.
    OUT.mkdir(parents=True,exist_ok=True)
    for n,t in contents.items():
        temp=OUT/('.'+n+'.tmp');temp.write_text(t,encoding='utf-8');temp.replace(OUT/n)
    print(json.dumps({'rules':metadata['counts'],'dns_host_mappings':len(mappings)},ensure_ascii=False))

if __name__=='__main__':build()
