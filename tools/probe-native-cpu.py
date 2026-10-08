"""Execute the original CPU machine code in Unicorn and audit the export.

Run from the repository root. Developer-only dependencies: pefile, unicorn.
Optional --write-fixture regenerates tests/fixtures/native-cpu-trace.lton.
The donor executable is read, never modified or launched as a process.
"""
import sys,struct,random,json
from pathlib import Path
sys.path[:0]=['build/inspect-python','tools/fm2k_convert']
import pefile,unicorn
from unicorn.x86_const import *
from cpu_data import names,locate,command_history,DIRECTIONS
from story import table_field,DONOR
from names import official
exe=next(DONOR.glob('*.exe')); pe=pefile.PE(str(exe)); u=unicorn.Uc(unicorn.UC_ARCH_X86,unicorn.UC_MODE_32)
u.mem_map(0x400000,0x400000); u.mem_write(pe.OPTIONAL_HEADER.ImageBase,pe.get_memory_mapped_image())
def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def get(a):return struct.unpack('<i',u.mem_read(a,4))[0]
seed=123
class NativeRandom:
 def seed(self,n):self.value=n
 def randrange(self,n):
  self.value=(self.value*214013+2531011)&0xffffffff
  return (self.value>>16)&32767
rng=NativeRandom();rng.seed(seed);rolls=[]
def hook(u,a,size,data):
 if a not in (0x403300,0x417a22,0x4179d0):return
 esp=u.reg_read(UC_X86_REG_ESP)
 if a==0x403300:u.mem_write(get(esp+4),bytes(get(esp+8)))
 elif a==0x417a22:
  v=rng.randrange(32768);rolls.append(v);u.reg_write(UC_X86_REG_EAX,v)
 else:u.reg_write(UC_X86_REG_EAX,0)
 u.reg_write(UC_X86_REG_EIP,get(esp));u.reg_write(UC_X86_REG_ESP,esp+4)
u.hook_add(unicorn.UC_HOOK_CODE,hook)
slot=0x4d1d80; enemy=slot+0xe03f; obj=0x600000; eobj=0x601000
put(0x4cfa00,obj);put(obj+0x156,0);put(eobj+0x156,1)
put(slot+0xdf5d,1);put(slot+0xdf65,1);put(slot+0xdf69,eobj)
put(slot+0xdef5,obj);put(enemy+0xdef5,eobj);put(0x47004c,1)
put(obj+0x58,920<<16);put(eobj+0x58,920<<16)
put(slot+0xdf45,920<<16);put(enemy+0xdf45,920<<16)
put(slot+0xdf41,500<<16);put(enemy+0xdf41,800<<16)
put(0x447ee0,100)
def run():
 esp=0x7ff000;put(esp,0x700000);u.reg_write(UC_X86_REG_ESP,esp)
 u.emu_start(0x411270,0x700000,count=100000)
def history(n):return [get(0x4280e0+((100-i)%1024)*4) for i in range(n)]
count=0
for source in DONOR.glob('*.player'):
 name=official(source.stem);path=Path('data/characters')/name/'data.lton'
 if not path.exists() or name=='だみー':continue
 data=path.read_text(encoding='utf-8'); raw=source.read_bytes(); labels=names(table_field(data,'commands'));at=locate(raw,labels,82)
 u.mem_write(slot+0x4da2,raw[at:at+82*len(labels)])
 put(slot+0xdf61,100)
 for command in range(1,len(labels)+1):
  record=raw[at+(command-1)*82:at+command*82]
  for direction in (0,2,6):
   u.mem_write(slot+0x2246,bytes(111));u.mem_write(slot+0x2246+42,struct.pack('<HHH',0x2000|direction,command,10))
   put(slot+0xdf75,1);put(slot+0xdf79,10);put(slot+0xdf81,0)
   run();expected=[0 if m<0 else m|DIRECTIONS[direction] for m in command_history(record)]
   assert history(len(expected)+1)==expected+[0],(name,command,direction,history(12),expected)
   count+=1
print('PASS native CPU command-history comparison:',count,'command/direction combinations')
# Record a complete native Ayane schedule for a matching L^ replay.
source=DONOR/'みこ.player';raw=source.read_bytes();data=Path('data/characters/あやね/data.lton').read_text(encoding='utf-8')
at=locate(raw,names(table_field(data,'cpu')),111);u.mem_write(slot+0x2246,raw[at:at+11100])
at=locate(raw,names(table_field(data,'commands')),82);u.mem_write(slot+0x4da2,raw[at:at+82*len(names(table_field(data,'commands')))])
traces=[]
for level in (0,20,60,100):
 rng.seed(seed);rolls.clear()
 for off in (0xdf75,0xdf79,0xdf7d):put(slot+off,0)
 put(slot+0xdf81,-1);put(slot+0xdf61,level)
 rows=[]
 for frame in range(400):
  distance=(80,240,400,600)[(frame//100)%4];put(enemy+0xdf41,(500+distance)<<16)
  put(slot+0xdf45,(900 if frame%100>=50 else 920)<<16)
  put(enemy+0xdf45,(900 if frame%160>=80 else 920)<<16)
  run();rows.append([get(slot+o) for o in (0xdf75,0xdf81,0xdf79,0xdf7d)]+[history(1)[0]])
 traces.append(dict(level=level,rolls=list(rolls),rows=rows))
Path('build/native-cpu-trace.json').write_text(json.dumps(traces))
print('Native scheduler traces: 4 levels x 400 frames')

if '--write-fixture' in sys.argv:
 output = '# Original EXE 0x411270, MSVCRT seed 123. See tools/probe-native-cpu.py.\ncases = {\n'
 for t in traces:
  output += ' { level = %d, rows = {\n' % t['level']
  output += '\n'.join('  { ' + ', '.join(map(str,row)) + ' },' for row in t['rows'])
  output += '\n } },\n'
 Path('tests/fixtures/native-cpu-trace.lton').write_text(output+'},\n',encoding='utf-8')
