"""Genera avatares anime vectoriales nítidos y expresiones locales para STOP-MULTIJUGADOR.
Los SVG son originales, escalables y transparentes fuera del retrato.
"""
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'frontend/assets/avatars'
EMOTIONS = ['normal','feliz','muy_feliz','triste','frustrado','sorprendido','concentrado','nervioso','pensativo','competitivo','suspenso','orgulloso']
CHARS = [
# name, skin, hair, secondary, outfit, hair silhouette, traits
('Goku','#f5c49a','#17151d','#f7a928','#ed7135','spiky','human'),
('Vegeta','#efbd91','#17151d','#3158c9','#243f83','vegeta','human'),
('Gohan','#f3c29a','#211922','#6d3bb8','#5132a0','shortspiky','human'),
('Piccolo','#6acb68','#177b45','#b9e8d7','#f2f0dc','antenna','green'),
('Trunks','#f3c7a8','#a78be6','#4a9ce9','#3854a6','bob','human'),
('Goten','#f3c19a','#17151b','#f6a928','#ef8a24','childspiky','human'),
('Krilin','#f3c19b','#7d3c24','#f18a37','#e66a25','bald','human'),
('Bulma','#f4c7a5','#20b9d2','#167eaa','#e94f95','bulma','human'),
('Androide 18','#f4c7a7','#d9c27d','#e9e0bd','#426d8e','longbob','human'),
('Androide 17','#f2c29e','#171b24','#c5e7ee','#2f465a','longdark','human'),
('Freezer','#eee5f4','#f3f0fb','#9562d8','#f0e8f7','alien','alien'),
('Cell','#a9d95e','#28764b','#83bd3f','#305f43','cell','green'),
('Majin Buu','#f0a3b8','#ef9bb1','#8f65cb','#8657bd','buu','pink'),
('Broly','#eac39a','#b4d64e','#d8e4a4','#4e9a54','broly','human'),
('Yamcha','#efbd94','#211b1b','#b36a36','#a84f24','longspiky','human'),
('Ten Shin Han','#f1c6a2','#171b24','#7e8fa8','#687b9c','flat','third_eye'),
('Bills','#9a72c7','#6b4ca1','#b28be2','#7048a7','cat','cat'),
('Whis','#bfe8ef','#8bd5ec','#e5f6ff','#3d82bc','high','blue'),
('Videl','#f3c39e','#1e1b25','#3a3a43','#cf477e','videl','human'),
('Bardock','#efbd94','#17151a','#2a493d','#4b8d46','bardock','human'),
]

HAIR_PATHS = {
'spiky':'M55 91 L36 56 L69 69 L61 28 L94 55 L111 17 L132 53 L159 25 L162 61 L199 45 L184 82 L208 91 L183 112 L72 112 Z',
'vegeta':'M54 96 L39 51 L73 68 L78 22 L103 55 L125 10 L145 54 L168 25 L170 61 L198 43 L184 88 L166 105 L72 108 Z',
'shortspiky':'M56 91 L42 61 L74 69 L76 39 L101 56 L121 28 L143 58 L165 36 L166 68 L194 55 L184 91 L166 106 L73 108 Z',
'antenna':'M55 92 Q50 49 75 45 Q66 15 88 19 Q109 21 103 49 L125 40 Q147 31 155 47 Q177 31 195 53 L184 91 L169 110 L74 110 Z',
'bob':'M48 84 Q43 38 81 34 Q121 10 162 34 Q203 43 198 91 L184 131 L169 92 L74 96 L60 129 Z',
'childspiky':'M55 91 L40 59 L72 69 L75 35 L98 56 L118 24 L141 56 L164 35 L167 69 L194 55 L184 92 L166 107 L73 108 Z',
'bald':'M57 83 Q62 35 125 34 Q184 35 191 83 L181 100 L72 100 Z',
'bulma':'M50 87 Q42 36 87 31 Q130 12 170 35 Q203 49 196 97 L183 130 L167 89 L75 91 L61 125 Z',
'longbob':'M48 82 Q43 33 90 29 Q138 10 173 39 Q204 56 196 100 L191 153 L174 133 L177 90 L76 90 L66 140 L53 123 Z',
'longdark':'M48 83 Q43 35 91 29 Q137 13 172 39 Q204 52 197 101 L191 151 L174 136 L177 89 L75 89 L63 139 L51 123 Z',
'alien':'M57 80 Q58 39 93 31 L84 18 L111 28 L132 18 L143 31 Q184 36 193 79 L180 105 L75 105 Z',
'cell':'M49 90 L42 50 L70 63 L75 25 L101 49 L121 12 L143 49 L170 24 L171 61 L197 45 L188 88 L169 109 L72 109 Z',
'buu':'M77 83 Q66 54 82 31 Q93 16 106 25 L126 3 L137 29 Q163 12 173 36 Q190 62 176 91 L161 108 L87 108 Z',
'broly':'M49 89 L34 56 L67 63 L60 29 L92 50 L98 12 L123 46 L147 10 L156 49 L186 25 L178 60 L207 55 L186 91 L168 110 L72 110 Z',
'longspiky':'M52 90 L38 56 L70 67 L77 34 L98 55 L118 20 L141 56 L162 31 L167 66 L198 50 L184 90 L171 108 L72 108 Z',
'flat':'M53 86 Q54 36 125 33 Q190 35 192 86 L181 100 L72 100 Z',
'cat':'M50 84 L39 45 L75 59 L83 32 L111 49 L128 19 L149 50 L178 31 L183 62 L207 51 L190 91 L171 108 L73 108 Z',
'high':'M57 82 Q54 43 89 37 L82 13 Q123 28 132 5 Q156 22 153 40 Q189 41 194 82 L181 102 L73 102 Z',
'videl':'M48 86 Q43 36 88 31 Q126 13 164 36 Q200 50 194 94 L185 124 L170 91 L76 91 L63 123 Z',
'bardock':'M50 90 L35 58 L67 66 L63 35 L91 52 L106 19 L126 48 L151 20 L157 54 L188 36 L178 67 L204 59 L185 94 L167 110 L72 109 Z',
}

EMOTION = {
'normal': ('M76 118 Q94 108 111 118','M145 118 Q163 108 180 118','M91 146 Q128 153 165 146','M111 179 Q128 184 145 179'),
'feliz': ('M76 116 Q94 126 111 116','M145 116 Q163 126 180 116','M91 144 Q128 151 165 144','M99 171 Q128 202 157 171'),
'muy_feliz': ('M74 113 Q94 131 113 113','M143 113 Q162 131 182 113','M90 142 Q128 151 166 142','M91 165 Q128 214 165 165'),
'triste': ('M76 113 Q94 103 111 119','M145 119 Q163 103 180 113','M91 150 Q128 139 165 150','M105 185 Q128 166 151 185'),
'frustrado': ('M76 121 L111 113','M145 113 L180 121','M91 146 Q128 137 165 146','M103 182 Q128 164 153 182'),
'sorprendido': ('M76 112 Q94 104 111 112','M145 112 Q163 104 180 112','M91 145 Q128 155 165 145','M111 169 Q128 159 145 169'),
'concentrado': ('M76 116 L111 119','M145 119 L180 116','M91 146 Q128 141 165 146','M110 179 Q128 175 146 179'),
'nervioso': ('M76 113 Q94 108 111 116','M145 116 Q163 108 180 113','M91 146 Q128 154 165 146','M113 176 Q128 169 143 176'),
'pensativo': ('M76 117 Q94 110 111 117','M145 117 Q163 110 180 117','M91 146 Q128 149 165 146','M112 179 Q128 171 144 179'),
'competitivo': ('M76 121 L111 112','M145 112 L180 121','M91 145 Q128 138 165 145','M104 175 Q128 185 152 175'),
'suspenso': ('M76 116 Q94 108 111 116','M145 116 Q163 108 180 116','M91 146 Q128 152 165 146','M114 177 Q128 172 142 177'),
'orgulloso': ('M76 115 Q94 121 111 115','M145 115 Q163 121 180 115','M91 145 Q128 153 165 145','M101 172 Q128 192 155 172'),
}

def make_svg(i, char, emotion):
    name, skin, hair, secondary, outfit, style, trait = char
    brow_l,brow_r,eye_line,mouth = EMOTION[emotion]
    # emotion-specific eye and mouth detail
    if emotion in ('sorprendido','nervioso','suspenso'):
        eyes = '<ellipse cx="94" cy="129" rx="10" ry="13" fill="#fff" stroke="#302333" stroke-width="4"/><ellipse cx="162" cy="129" rx="10" ry="13" fill="#fff" stroke="#302333" stroke-width="4"/><ellipse cx="96" cy="131" rx="4" ry="7" fill="#342d38"/><ellipse cx="160" cy="131" rx="4" ry="7" fill="#342d38"/>'
    elif emotion in ('feliz','muy_feliz','orgulloso'):
        eyes = '<path d="M80 130 Q94 116 108 130" fill="none" stroke="#302333" stroke-width="6" stroke-linecap="round"/><path d="M148 130 Q162 116 176 130" fill="none" stroke="#302333" stroke-width="6" stroke-linecap="round"/>'
    elif emotion == 'triste':
        eyes = '<ellipse cx="94" cy="130" rx="9" ry="8" fill="#fff" stroke="#302333" stroke-width="4"/><ellipse cx="162" cy="130" rx="9" ry="8" fill="#fff" stroke="#302333" stroke-width="4"/><circle cx="96" cy="132" r="4" fill="#302333"/><circle cx="160" cy="132" r="4" fill="#302333"/><path d="M177 142 Q185 153 177 162 Q170 153 177 142Z" fill="#7bd9ff"/>'
    else:
        eyes = '<ellipse cx="94" cy="130" rx="10" ry="9" fill="#fff" stroke="#302333" stroke-width="4"/><ellipse cx="162" cy="130" rx="10" ry="9" fill="#fff" stroke="#302333" stroke-width="4"/><ellipse cx="97" cy="131" rx="5" ry="7" fill="#302333"/><ellipse cx="159" cy="131" rx="5" ry="7" fill="#302333"/>'
    if emotion in ('muy_feliz','sorprendido'):
        mouth_svg = '<ellipse cx="128" cy="178" rx="17" ry="21" fill="#632d3c" stroke="#302333" stroke-width="4"/><path d="M113 178 Q128 187 143 178" fill="none" stroke="#f5a0aa" stroke-width="4"/>'
    elif emotion in ('feliz','orgulloso'):
        mouth_svg = '<path d="M96 172 Q128 205 160 172 Q128 188 96 172Z" fill="#8d3344" stroke="#302333" stroke-width="4" stroke-linejoin="round"/><path d="M108 177 Q128 184 148 177" fill="none" stroke="#fff2e9" stroke-width="5"/>'
    elif emotion == 'triste':
        mouth_svg = '<path d="M107 185 Q128 166 149 185" fill="none" stroke="#713646" stroke-width="5" stroke-linecap="round"/>'
    elif emotion == 'frustrado':
        mouth_svg = '<path d="M108 183 Q128 168 148 183 L142 189 L114 189Z" fill="#632d3c" stroke="#302333" stroke-width="4"/>'
    else:
        mouth_svg = f'<path d="{mouth}" fill="none" stroke="#713646" stroke-width="5" stroke-linecap="round"/>'
    if trait == 'green': skin2='#b8ed96'; ears='<path d="M67 126 L42 113 L60 145Z" fill="'+skin+'" stroke="#302333" stroke-width="4"/><path d="M189 126 L214 113 L196 145Z" fill="'+skin+'" stroke="#302333" stroke-width="4"/>'
    elif trait == 'alien': skin2='#f6f1fb'; ears='<path d="M67 126 L47 115 L62 145Z" fill="'+skin+'" stroke="#302333" stroke-width="4"/><path d="M189 126 L209 115 L194 145Z" fill="'+skin+'" stroke="#302333" stroke-width="4"/>'
    elif trait == 'pink': skin2='#ffc0cf'; ears=''
    elif trait == 'cat': skin2='#bd9bdf'; ears='<path d="M65 105 L52 66 L88 86Z" fill="'+hair+'" stroke="#302333" stroke-width="4"/><path d="M191 105 L204 66 L168 86Z" fill="'+hair+'" stroke="#302333" stroke-width="4"/>'
    elif trait == 'blue': skin2='#d5f5f5'; ears=''
    else: skin2=skin; ears='<path d="M67 132 Q48 124 53 145 Q58 159 74 151Z" fill="'+skin+'" stroke="#302333" stroke-width="4"/><path d="M189 132 Q208 124 203 145 Q198 159 182 151Z" fill="'+skin+'" stroke="#302333" stroke-width="4"/>'
    if trait == 'third_eye': third='<ellipse cx="128" cy="89" rx="12" ry="9" fill="#fff" stroke="#302333" stroke-width="3"/><ellipse cx="128" cy="89" rx="4" ry="6" fill="#302333"/>'
    else: third=''
    if trait in ('alien','green','pink','cat','blue'):
        nose = '<path d="M126 137 L121 151 Q128 156 135 151" fill="none" stroke="#67465b" stroke-width="3" stroke-linecap="round"/>'
    else:
        nose = '<path d="M127 136 L123 151 L131 153" fill="none" stroke="#a76b65" stroke-width="3" stroke-linecap="round"/>'
    if style == 'bald': hair_top=''
    else: hair_top=f'<path d="{HAIR_PATHS[style]}" fill="url(#hair)" stroke="#24202b" stroke-width="5" stroke-linejoin="round"/>'
    if style in ('spiky','vegeta','shortspiky','childspiky','cell','broly','longspiky','cat','bardock'):
        hair_glints='<path d="M72 70 L88 79 M109 46 L119 63 M153 47 L163 61 M177 66 L188 67" stroke="'+secondary+'" stroke-width="5" stroke-linecap="round" opacity=".85" fill="none"/>'
    else:
        hair_glints='<path d="M72 59 Q103 27 142 39" stroke="'+secondary+'" stroke-width="5" stroke-linecap="round" opacity=".85" fill="none"/>'
    if name == 'Goku': outfit_extra='<path d="M76 220 L91 240 L128 251 L165 240 L180 220" fill="none" stroke="#f8bb3f" stroke-width="7"/>'
    elif name == 'Vegeta': outfit_extra='<path d="M92 220 L164 220 L151 245 L105 245Z" fill="#f0f4f8" stroke="#293244" stroke-width="4"/>'
    elif name in ('Piccolo','Cell'): outfit_extra='<path d="M82 218 L103 238 L128 229 L153 238 L174 218" fill="none" stroke="'+secondary+'" stroke-width="8"/>'
    else: outfit_extra='<path d="M89 221 Q128 237 167 221" fill="none" stroke="'+secondary+'" stroke-width="6" opacity=".9"/>'
    # thoughtful/nervous marks are small, vector and readable at small sizes
    extras = ''
    if emotion == 'pensativo': extras='<path d="M184 104 Q202 92 210 105" fill="none" stroke="#f6d66a" stroke-width="4" stroke-linecap="round"/><circle cx="211" cy="94" r="4" fill="#f6d66a"/>'
    elif emotion == 'nervioso': extras='<path d="M183 145 Q198 153 192 166" fill="none" stroke="#80d9ff" stroke-width="4" stroke-linecap="round"/><circle cx="190" cy="170" r="3" fill="#80d9ff"/>'
    elif emotion == 'competitivo': extras='<path d="M54 90 L43 79 M202 89 L213 78" stroke="#ffcc46" stroke-width="5" stroke-linecap="round"/>'
    elif emotion == 'orgulloso': extras='<path d="M187 105 Q202 96 210 104" fill="none" stroke="#ffce4d" stroke-width="4" stroke-linecap="round"/>'
    elif emotion == 'suspenso': extras='<path d="M188 96 Q203 82 216 95" fill="none" stroke="#9fe8ff" stroke-width="4" stroke-linecap="round"/><circle cx="215" cy="86" r="4" fill="#9fe8ff"/>'
    # little cheek accents, kept subtle for clarity
    blush = '<path d="M75 157 l14 -3 M167 154 l14 3" stroke="#ef8e91" stroke-width="4" stroke-linecap="round" opacity=".7"/>' if emotion in ('feliz','muy_feliz','nervioso') else ''
    title=escape(f'{name} - {emotion.replace("_"," ")}')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="{title}"><title>{title}</title>
<defs><linearGradient id="skin" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{skin2}"/><stop offset=".55" stop-color="{skin}"/><stop offset="1" stop-color="{skin}"/></linearGradient><linearGradient id="hair" x1="0" y1="0" x2=".8" y2="1"><stop offset="0" stop-color="{secondary}"/><stop offset=".45" stop-color="{hair}"/><stop offset="1" stop-color="{hair}"/></linearGradient><linearGradient id="cloth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{secondary}"/><stop offset="1" stop-color="{outfit}"/></linearGradient></defs>
<!-- hombros y uniforme --> <path d="M35 256 Q38 218 69 207 L94 198 L162 198 L187 207 Q218 218 221 256Z" fill="url(#cloth)" stroke="#282231" stroke-width="5"/><path d="M88 204 L105 226 L128 240 L151 226 L168 204" fill="none" stroke="#fff" stroke-width="5" opacity=".8"/>{outfit_extra}
<!-- cuello --> <path d="M103 177 L103 211 Q128 230 153 211 L153 177Z" fill="url(#skin)" stroke="#302333" stroke-width="4"/>
<!-- orejas y rostro --> {ears}<path d="M72 93 Q73 65 128 63 Q183 65 184 93 L179 148 Q173 183 128 198 Q83 183 77 148Z" fill="url(#skin)" stroke="#302333" stroke-width="5" stroke-linejoin="round"/>
<!-- flequillo posterior --> {('<path d="M60 101 Q48 70 70 48 Q91 22 128 29 Q170 22 191 52 Q208 75 195 108 L182 88 Q166 78 156 65 L136 91 L121 61 L103 89 L87 75 L74 103Z" fill="url(#hair)" stroke="#24202b" stroke-width="5" stroke-linejoin="round"/>' if style != 'bald' else '')}
{hair_top}{hair_glints}
<!-- cejas --> <path d="{brow_l}" fill="none" stroke="#302333" stroke-width="6" stroke-linecap="round"/><path d="{brow_r}" fill="none" stroke="#302333" stroke-width="6" stroke-linecap="round"/>
<!-- ojos --> {eyes}<path d="M80 141 Q94 145 108 141 M148 141 Q162 145 176 141" fill="none" stroke="#fff" stroke-width="2" opacity=".5"/>
<!-- nariz y boca --> {nose}{mouth_svg}{blush}{third}{extras}
<!-- reflejos de pelo y contorno facial --> <path d="M76 101 Q82 83 99 77 M158 76 Q175 80 181 99" fill="none" stroke="{secondary}" stroke-width="4" stroke-linecap="round" opacity=".85"/>
</svg>'''

def main():
    count=0
    for i,char in enumerate(CHARS,1):
        avatar_id=f'persona-{i:02d}'
        for emotion in EMOTIONS:
            svg=make_svg(i,char,emotion)
            if emotion=='normal':
                (DEST/f'{avatar_id}.svg').write_text(svg+'\n',encoding='utf-8')
            folder=DEST/'expresiones'/avatar_id
            folder.mkdir(parents=True,exist_ok=True)
            (folder/f'{emotion}.svg').write_text(svg+'\n',encoding='utf-8')
            count+=1
    print(f'{count} expresiones vectoriales generadas para {len(CHARS)} avatares.')
if __name__=='__main__': main()
