import json, random, secrets, threading, os, socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
rooms={}; lock=threading.RLock()
Q=[('恋愛','恋人に求める条件は？','顔|面白さ|誠実さ|経済力|価値観|安心感'),('恋愛','理想の初デートは？','水族館|ドライブ|居酒屋|映画|遊園地|夜景'),('恋愛','好きになるきっかけは？','笑顔|ギャップ|香り|優しさ|会話|見た目'),('恋愛','恋人にされたら嬉しいことは？','サプライズ|毎日電話|会いに来る|手紙|褒める|そばにいる'),('恋愛','別れを考える理由は？','嘘|束縛|浮気|会話不足|金銭感覚|将来性'),('価値観','人生で大切なものは？','お金|友情|恋愛|家族|自由|仕事'),('価値観','100万円を使うなら？','旅行|投資|ブランド品|趣味|貯金|豪遊'),('価値観','褒められて嬉しいことは？','頭の良さ|容姿|優しさ|面白さ|努力|センス'),('価値観','人生で避けたいことは？','孤独|貧乏|退屈|失敗|後悔|不自由'),('深夜','一番ドキッとする仕草は？','目を見つめる|耳元で話す|手を握る|髪をかき上げる|距離が近い|甘える'),('深夜','嫉妬してしまう状況は？','元恋人の話|異性と二人で飲む|毎日LINE|異性を褒める|異性と旅行|友達優先'),('深夜','恋愛で沼りそうな相手は？','気まぐれ|モテる|自分だけに優しい|追ってこない|甘え上手|ギャップ'),('深夜','知られたら恥ずかしいものは？','検索履歴|昔のLINE|昔の写真|スマホのメモ|恋愛遍歴|一人の行動'),('深夜','恋愛で弱いシチュエーションは？','終電後|二人きりのドライブ|夜中の電話|不意のハグ|帰り際|夜景'),('究極の選択','一生無料になるなら？','家賃|外食|旅行|洋服|交通費|娯楽'),('究極の選択','手に入れたい能力は？','瞬間移動|時間停止|読心術|未来予知|透明人間|過去に戻る'),('究極の選択','絶対叶うなら？','健康|大富豪|理想の結婚|世界一周|仕事の成功|若さ'),('メンバー','この中でモテそうな人は？','@'),('メンバー','この中で結婚が早そうな人は？','@'),('メンバー','この中で将来お金持ちになりそうな人は？','@'),('メンバー','この中で相談したい人は？','@'),('メンバー','この中で旅行したら楽しそうな人は？','@')]
def newq(r):
 p=[i for i,q in enumerate(Q) if (r['mode']=='全部' or q[0]==r['mode']) and i not in r['used']]
 if not p:r['used']=[];return newq(r)
 i=random.choice(p);r['used'].append(i);cat,q,c=Q[i];r.update(q=q,cat=cat,choices=[x['name'] for x in r['players']] if c=='@' else c.split('|'),answers={},phase='play')
def state(r,p):
 out={k:v for k,v in r.items() if k not in ('answers','used','players','host')};out['players']=[{k:v for k,v in x.items() if k!='id'} for x in r['players']];out['me']=next(i for i,x in enumerate(r['players']) if x['id']==p);out['host']=p==r['host'];out['done']=len(r['answers']);out['submitted']=p in r['answers'];out['judge']=r['round']%len(r['players']);
 if r['phase']=='result':out['results']=[r['answers'].get(x['id']) for x in r['players']]
 return out
class H(BaseHTTPRequestHandler):
 def send(self,obj,status=200):
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.path.split('?')[0]=='/':
   b=Path(__file__).with_name('index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b)
  else:self.send({},404)
 def do_POST(self):
  try:
   d=json.loads(self.rfile.read(int(self.headers['Content-Length'])));a=d['action'];p=d.get('token');code=d.get('code','').upper();name=str(d.get('name','')).strip()[:20]
   with lock:
    if a=='create':
     if not name:raise ValueError('名前を入力してください')
     code=secrets.token_hex(3).upper();p=secrets.token_urlsafe(24);r={'players':[{'id':p,'name':name,'score':0}],'host':p,'phase':'lobby','round':0,'total':0,'used':[],'answers':{},'mode':'全部','code':code};rooms[code]=r;return self.send({'token':p,'code':code})
    r=rooms.get(code)
    if not r:raise ValueError('ルームが見つかりません')
    if a=='join':
     if r['phase']!='lobby' or len(r['players'])>=12 or not name:raise ValueError('参加できません')
     p=secrets.token_urlsafe(24);r['players'].append({'id':p,'name':name,'score':0});return self.send({'token':p,'code':code})
    if p not in [x['id'] for x in r['players']]:raise ValueError('参加情報が無効です')
    if a in ('start','next','skip') and p!=r['host']:raise ValueError('ホストのみ操作できます')
    if a=='start' and r['phase']=='lobby':
     if len(r['players'])<3:raise ValueError('3人以上必要です')
     r['mode']=d.get('mode','全部');assert r['mode'] in ['全部']+[q[0] for q in Q];r['total']=len(r['players'])*(2 if d.get('cycles')==2 else 1);newq(r)
    elif a=='submit' and r['phase']=='play':
     v=d['ranks'];assert len(v)==3 and len(set(v))==3 and all(type(i)==int and 0<=i<len(r['choices']) for i in v)
     if p not in r['answers']:r['answers'][p]=v
     if len(r['answers'])==len(r['players']):
      j=r['round']%len(r['players']);ans=r['answers'][r['players'][j]['id']]
      for i,x in enumerate(r['players']):
       m=sum(a==b for a,b in zip(ans,r['answers'][x['id']]));x['gain']=0 if i==j else (5 if m==3 else m);x['score']+=x['gain']
      r['phase']='result'
    elif a=='next' and r['phase']=='result':
     r['round']+=1
     if r['round']>=r['total']:r['phase']='final'
     else:newq(r)
    elif a=='skip' and r['phase']=='play':newq(r)
    return self.send(state(r,p))
  except Exception as e:self.send({'error':str(e) or '入力が無効です'},400)
if __name__=='__main__':
 port=int(os.getenv('PORT','8000'));print(f'Open http://localhost:{port} — other phones: http://<computer LAN IP>:{port}',flush=True);ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()
