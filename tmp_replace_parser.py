from pathlib import Path
path = Path(r'c:\Users\User\Desktop\matchup\matchup.html')
text = path.read_text(encoding='utf-8')
old = r'''function pf(sec,tag){const r=sec.match(new RegExp(`${tag}:\s*(.+?)(?=\n[A-Z0-9_]+:|$)`,'s'));if(!r)return '';let txt=r[1].trim();txt=txt.replace(/\*\*(.+?)\*\*/g,'$1');txt=txt.replace(/#{1,6}\s+/g,'');txt=txt.replace(/^\*\s+/gm,'');txt=txt.replace(/^-\s+/gm,'');return txt;}'''
new = r'''function normalizeReportRaw(raw){return String(raw||'').replace(/\r\n?/g,'\n').replace(/(^|\n)\s*TAB([1-4])\s*[:\-\)]?\s*/gmi,'$1[TAB$2]\n').replace(/(^|\n)\s*\[S([1-4])\]/gmi,'$1[TAB$2]');}
function ps(raw,tag){const normalized=normalizeReportRaw(raw);const r=normalized.match(new RegExp(`\[${tag}\]([\s\S]*?)(?=(\[TAB[1-4]\]|$))`,`i`));return r?r[1].trim():'';}
function pf(sec,tag){const r=sec.match(new RegExp(`${tag}:\s*([\s\S]*?)(?=\n\s*[A-Z0-9_ ]+:|$)`,`i`));return r?r[1].trim():'';}'''
if old not in text:
    raise ValueError('OLD parser line not found')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('parser helper updated')
