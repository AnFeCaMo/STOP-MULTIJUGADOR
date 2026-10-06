import asyncio, random, secrets, time
from dataclasses import dataclass, field
from typing import Any, Optional

CATEGORIES = ["nombre", "apellido", "ciudad", "fruta", "animal", "cosa"]
LETTERS = list("ABCDEFGLMPRSTV")
AVATARS = ["🐻","🐔","🐱","🐶","🐵","🦊","🐸","🐼","🐨","🐯","🦁","🐰","🐷","🐮","🐧","🦄","🤖","👽","👾","👻","🎃"]
REACTIONS = ["😂 JAJA","😎 Fácil","😏 Te gané","🔥 ¡Vamos!","👏 Bien jugado","😱 ¿Qué pasó?","😭 No puede ser","🤔 Estoy pensando","🥳 ¡Ganamos!","❤️ Buena partida"]
ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def clean_name(v: Any) -> str:
    return str(v or "").strip()[:24]


def valid_avatar(v: Any) -> str:
    return v if v in AVATARS else AVATARS[0]

@dataclass
class Player:
    id: str
    token: str
    name: str
    avatar: str = "🐻"
    ws: Any = None
    connected: bool = True
    host: bool = False
    spectator: bool = False
    status: str = "Conectado"
    score: int = 0
    wins: int = 0
    rounds_won: int = 0
    valid: int = 0
    rejected: int = 0
    submitted: int = 0
    stops: int = 0
    streak: int = 0
    best_streak: int = 0
    achievements: set = field(default_factory=set)
    answers: dict = field(default_factory=dict)
    round_score: int = 0
    disconnected_at: float = 0.0
    typing: bool = False

@dataclass
class Room:
    code: str
    players: dict = field(default_factory=dict)
    state: str = "SALA"
    host_id: Optional[str] = None
    round: int = 0
    total_rounds: int = 4
    categories: list = field(default_factory=lambda: CATEGORIES[:])
    letter: str = ""
    used_letters: list = field(default_factory=list)
    deadline: float = 0.0
    stop_by: Optional[str] = None
    vote_items: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    abandoned_at: float = 0.0
    timer_task: Any = None
    stats: dict = field(default_factory=lambda: {"rounds":0,"valid":0,"rejected":0,"submitted":0,"stops":0})

class V4Game:
    def __init__(self, reconnect_window=180, cleanup_window=600):
        self.rooms: dict[str, Room] = {}
        self.tokens: dict[str, tuple[str,str]] = {}
        self.lock = asyncio.Lock()
        self.reconnect_window = reconnect_window
        self.cleanup_window = cleanup_window

    def new_code(self):
        while True:
            code = "".join(random.choice(ROOM_ALPHABET) for _ in range(4))
            if code not in self.rooms:
                return code

    async def create_room(self, name, avatar="🐻"):
        async with self.lock:
            code = self.new_code(); pid = secrets.token_hex(8); token = secrets.token_urlsafe(32)
            room = Room(code=code); p = Player(pid, token, clean_name(name), valid_avatar(avatar))
            p.host = True; room.host_id = pid; room.players[pid] = p
            self.rooms[code] = room; self.tokens[token] = (code,pid)
            return self.session(room,p), None

    async def join_room(self, code, name, avatar="🐻", token=None, ws=None):
        async with self.lock:
            room = self.rooms.get(str(code or "").upper())
            if not room: return None, "Sala inexistente."
            name = clean_name(name)
            if not name: return None, "El nombre es obligatorio."
            if token and token in self.tokens:
                r,pid = self.tokens[token]
                if r == room.code and pid in room.players:
                    p=room.players[pid]; p.ws=ws; p.connected=True; p.status="Conectado"; p.disconnected_at=0
                    return self.session(room,p,reconnected=True), None
            if any(p.name.casefold()==name.casefold() and p.connected for p in room.players.values()):
                return None, "Ya existe un jugador conectado con ese nombre."
            pid=secrets.token_hex(8); token=secrets.token_urlsafe(32)
            spectator = room.state in {"JUEGO","VOTACION","RESULTADOS"}
            p=Player(pid,token,name,valid_avatar(avatar),ws=ws,spectator=spectator,status="Espectador" if spectator else "Conectado")
            room.players[pid]=p; self.tokens[token]=(room.code,pid)
            if room.host_id is None and not spectator: self.set_host(room,pid)
            return self.session(room,p), None

    def set_host(self, room, pid):
        room.host_id=pid
        for p in room.players.values(): p.host=(p.id==pid)

    def session(self,room,p,reconnected=False):
        return {"room":room.code,"id":p.id,"token":p.token,"name":p.name,"avatar":p.avatar,"host":p.host,"spectator":p.spectator,"reconnected":reconnected}

    def attach(self, room_code, pid, ws):
        room=self.rooms.get(room_code); p=room.players.get(pid) if room else None
        if not p: return False
        p.ws=ws; p.connected=True; p.status="Conectado"; p.disconnected_at=0; return True

    async def disconnect(self, room_code, pid, ws=None):
        async with self.lock:
            room=self.rooms.get(room_code); p=room.players.get(pid) if room else None
            if not p or (ws is not None and p.ws is not ws): return None
            p.ws=None; p.connected=False; p.status="Desconectado"; p.disconnected_at=time.time()
            if room.host_id==pid:
                connected=[x.id for x in room.players.values() if x.connected and not x.spectator]
                if connected: self.set_host(room,connected[0])
                else: room.host_id=None
            if not any(x.connected for x in room.players.values()): room.abandoned_at=time.time()
            return p.name

    def purge(self):
        now=time.time(); removed=[]
        for code,room in list(self.rooms.items()):
            for pid,p in list(room.players.items()):
                if not p.connected and p.disconnected_at and now-p.disconnected_at>self.reconnect_window:
                    self.tokens.pop(p.token,None); del room.players[pid]
            if not room.players or (room.abandoned_at and now-room.abandoned_at>self.cleanup_window):
                for p in room.players.values(): self.tokens.pop(p.token,None)
                self.rooms.pop(code,None); removed.append(code)
        return removed

    def public_state(self,room):
        now=time.time(); remaining=max(0,int(room.deadline-now)) if room.state=="JUEGO" else 0
        players=[]
        for p in room.players.values():
            players.append({"id":p.id,"name":p.name,"avatar":p.avatar,"connected":p.connected,"status":p.status,"host":p.host,"spectator":p.spectator,"score":p.score,"round_score":p.round_score,"typing":p.typing,"wins":p.wins,"streak":p.streak})
        return {"tipo":"estado","room":room.code,"state":room.state,"round":room.round,"total_rounds":room.total_rounds,"letter":room.letter,"deadline":room.deadline,"remaining":remaining,"categories":room.categories,"players":players,"stop_by":room.stop_by,"vote_items":self.vote_public(room),"stats":room.stats}

    def vote_public(self,room):
        return [{"key":k,"category":v["category"],"answer":v["answer"],"authors":v["authors"],"yes":len(v["yes"]),"no":len(v["no"]),"voters":v["voters"]} for k,v in room.vote_items.items()]

    async def configure(self,room_code,pid,rounds,categories):
        async with self.lock:
            room=self.rooms.get(room_code); 
            if not room or room.host_id!=pid: return False,"Solo el anfitrión puede configurar."
            if room.state!="SALA": return False,"La configuración está bloqueada."
            if not isinstance(rounds,int) or not 4<=rounds<=10: return False,"Las rondas deben estar entre 4 y 10."
            cats=[c for c in categories or [] if c in CATEGORIES]
            if len(set(cats))<3: return False,"Selecciona al menos 3 categorías."
            room.total_rounds=rounds; room.categories=[c for c in CATEGORIES if c in cats]; return True,None

    async def start_round(self,room_code,pid):
        async with self.lock:
            room=self.rooms.get(room_code)
            if not room or room.host_id!=pid: return False,"Solo el anfitrión puede iniciar."
            if room.state not in {"SALA","RESULTADOS"}: return False,"La ronda ya está en curso."
            if room.round>=room.total_rounds: return False,"La partida terminó."
            letters=[x for x in LETTERS if x not in room.used_letters]
            if not letters: return False,"No quedan letras disponibles."
            room.round+=1; room.letter=random.choice(letters); room.used_letters.append(room.letter); room.stop_by=None; room.vote_items={}; room.state="JUEGO"; room.deadline=time.time()+60
            for p in room.players.values():
                p.round_score=0; p.answers={c:"" for c in room.categories}; p.typing=False
                if not p.spectator: p.status="Conectado"
            if room.timer_task and not room.timer_task.done(): room.timer_task.cancel()
            room.timer_task=asyncio.create_task(self._timer(room.code,room.round))
            return True,None

    async def _timer(self,code,round_no):
        try: await asyncio.sleep(60)
        except asyncio.CancelledError: return
        async with self.lock:
            room=self.rooms.get(code)
            if not room or room.round!=round_no or room.state!="JUEGO": return
            self._close_round(room,None)

    def submit(self,room,pid,answers):
        p=room.players.get(pid)
        if room.state!="JUEGO" or not p or p.spectator or not p.connected: return False,"No puedes responder ahora."
        if time.time()>=room.deadline: self._close_round(room,None); return False,"El tiempo terminó."
        for c in room.categories: p.answers[c]=str((answers or {}).get(c,""))[:80].strip()
        p.submitted= p.submitted + 1; p.status="Completó"; p.typing=False; room.stats["submitted"]+=1; return True,None

    def stop(self,room,pid,answers=None):
        p=room.players.get(pid)
        if room.state!="JUEGO": return False,"La ronda ya terminó."
        if not p or p.spectator or not p.connected: return False,"No puedes pulsar STOP."
        if room.stop_by: return False,"STOP ya fue presionado."
        if answers is not None: self.submit(room,pid,answers)
        room.stop_by=pid; p.stops+=1; room.stats["stops"]+=1; self._close_round(room,pid); return True,None

    def _close_round(self,room,stop_pid):
        room.deadline=0
        candidates={}
        for p in room.players.values():
            if p.spectator: continue
            p.round_score=0
            for c in room.categories:
                a=p.answers.get(c,"")
                if not a: continue
                p.round_score += 10
                p.valid += 1; room.stats["valid"]+=1
                key=f"{c}:{a.casefold()}"
                item=candidates.setdefault(key,{"category":c,"answer":a,"authors":[],"yes":set(),"no":set(),"voters":[]})
                item["authors"].append(p.id)
        for item in candidates.values():
            if len(item["authors"])>1: item["base_duplicate"]=True
            item["voters"]=[x.id for x in room.players.values() if x.connected and not x.spectator and x.id not in item["authors"]]
        room.vote_items=candidates
        room.state="VOTACION" if candidates else "RESULTADOS"
        if room.state=="RESULTADOS": self.finish_scores(room)

    def vote(self,room,pid,key,value):
        if room.state!="VOTACION": return False,"La votación no está activa."
        item=room.vote_items.get(key)
        if not item or pid not in item["voters"]: return False,"No puedes votar esta respuesta."
        if pid in item["yes"] or pid in item["no"]: return False,"Ya votaste esta respuesta."
        (item["yes"] if value else item["no"]).add(pid)
        if len(item["yes"]|item["no"])>=len(item["voters"]):
            room.state="RESULTADOS"; self.finish_scores(room)
        return True,None

    def finish_scores(self,room):
        for item in room.vote_items.values():
            accepted=len(item["authors"])==1 and (not item["voters"] or len(item["yes"])>=len(item["no"]))
            for pid in item["authors"]:
                p=room.players.get(pid)
                if not p: continue
                if accepted:
                    p.score+=10; p.round_score+=10; p.streak+=1; p.best_streak=max(p.best_streak,p.streak)
                else:
                    p.rejected+=1; p.streak=0; p.round_score=max(0,p.round_score-5)
        best=max((p.round_score for p in room.players.values()),default=0)
        for p in room.players.values():
            if not p.spectator and p.round_score==best and best>0: p.rounds_won+=1
            if p.round_score==best and best>0: p.achievements.add("⚡ Respuesta rápida")
            if p.streak>=3: p.achievements.add("🔥 3 rondas consecutivas")
        room.stats["rounds"]+=1
        if room.round>=room.total_rounds:
            room.state="FINAL"; self.finalize(room)

    def finalize(self,room):
        ranking=sorted([p for p in room.players.values() if not p.spectator],key=lambda p:(p.score,p.wins,p.best_streak),reverse=True)
        if ranking:
            ranking[0].wins+=1; ranking[0].achievements.add("🏆 Primera victoria"); ranking[0].achievements.add("👑 Campeón")
            if ranking[0].stops: ranking[0].achievements.add("😂 Rey del STOP")
            for p in ranking[1:]: p.streak=0

    def stats(self,room):
        ranking=sorted([p for p in room.players.values() if not p.spectator],key=lambda p:(p.score,p.wins,p.best_streak),reverse=True)
        return {"rounds":room.round,"players":len(ranking),"valid":room.stats["valid"],"rejected":sum(p.rejected for p in ranking),"submitted":room.stats["submitted"],"stops":room.stats["stops"],"ranking":[{"name":p.name,"avatar":p.avatar,"score":p.score,"wins":p.wins,"rounds_won":p.rounds_won,"valid":p.valid,"rejected":p.rejected,"streak":p.best_streak,"achievements":sorted(p.achievements)} for p in ranking]}

    def achievements(self,room,pid):
        p=room.players.get(pid); return sorted(p.achievements) if p else []

    def react(self,room,pid,text):
        return text if text in REACTIONS and pid in room.players else None

    async def new_game(self,room_code,pid):
        async with self.lock:
            room=self.rooms.get(room_code)
            if not room or room.host_id!=pid: return False,"Solo el anfitrión puede iniciar una nueva partida."
            if room.timer_task and not room.timer_task.done(): room.timer_task.cancel()
            room.state="SALA"; room.round=0; room.used_letters=[]; room.letter=""; room.stop_by=None; room.vote_items={}; room.history=[]
            for p in room.players.values(): p.score=0; p.wins=0; p.rounds_won=0; p.valid=0; p.rejected=0; p.submitted=0; p.stops=0; p.streak=0; p.best_streak=0; p.achievements=set(); p.spectator=False
            return True,None
