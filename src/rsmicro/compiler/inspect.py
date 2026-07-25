import struct,zlib,hashlib,json
from .image import *
def inspect_image(raw):
 if len(raw)<HEADER_SIZE: raise ValueError('truncated header')
 vals=struct.unpack_from(HEADER_FMT,raw); magic,major,minor,hs,total,pver,abi,count,uid,ch,crc=vals
 if magic!=MAGIC: raise ValueError('wrong magic')
 if (major,minor)!=VERSION: raise ValueError('unsupported image version')
 if total!=len(raw): raise ValueError('truncated or oversized image')
 check=bytearray(raw); struct.pack_into('<I',check,HEADER_SIZE-4,0)
 if zlib.crc32(check)&0xffffffff!=crc: raise ValueError('bad CRC')
 if hs+count*DESC_SIZE>len(raw): raise ValueError('truncated section table')
 rev={v:k for k,v in SECTIONS.items()}; sections=[]; spans=[]
 for n in range(count):
  typ,flags,off,length,entries,res=struct.unpack_from(DESC_FMT,raw,hs+n*DESC_SIZE)
  if typ not in rev: raise ValueError('unknown required section')
  if off<hs+count*DESC_SIZE or off+length>len(raw): raise ValueError('bad section offset')
  if any(not(off+length<=a or off>=b) for a,b in spans): raise ValueError('section overlap')
  spans.append((off,off+length)); sections.append({'type':rev[typ],'offset':off,'length':length,'flags':flags})
 if len({x['type'] for x in sections})!=len(sections): raise ValueError('duplicate required section')
 missing=set(SECTIONS)-{x['type'] for x in sections}
 if missing: raise ValueError('missing required section')
 def section(name):
  s=next(x for x in sections if x['type']==name); return raw[s['offset']:s['offset']+s['length']]
 tags=json.loads(section('TAG_TABLE')); stream=section('INSTRUCTION_STREAM'); mem=json.loads(section('MEMORY_ESTIMATES'))
 return {'magic':'RSM1','image_format':'1.0','profile':'RSM-LOGIX-CORE-1','instruction_abi':abi,'controller_uuid':__import__('uuid').UUID(bytes=uid).hex,'size':len(raw),'crc':f'{crc:08x}','crc_valid':True,'sha256':hashlib.sha256(raw).hexdigest(),'sections':sections,'tag_count':len(tags),'instruction_count':sum(1 for _ in iter_stream(stream)),'memory_estimates':mem}
def iter_stream(b):
 p=0
 while p<len(b):
  if p+12>len(b): raise ValueError('malformed instruction stream')
  op,n,_,iid=struct.unpack_from('<BBHI',b,p); yield op; p+=12+n*8
  if p>len(b): raise ValueError('malformed operand encoding')
