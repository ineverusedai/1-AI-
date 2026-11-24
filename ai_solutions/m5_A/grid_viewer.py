from PIL import Image
im=Image.open('frame.png').convert('RGB')
def px(x,y): return im.getpixel((29+8*x+4,29+8*y+4))
cols={}
for y in range(64):
  row=''
  for x in range(64):
    p=px(x,y); r,g,b=p
    c='.' if max(p)<40 else 'W' if min(p)>200 else 'R' if r>200 and g<100 and b<100 else 'B' if b>200 and r<100 and g<160 else 'O' if r>200 and 100<g<200 and b<80 else 'Y' if r>200 and g>200 and b<80 else 'G' if g>150 and r<100 and b<100 else 'g' if abs(r-g)<20 and abs(g-b)<20 and r>120 else 'd' if abs(r-g)<20 and abs(g-b)<20 else None
    if c is None:
      c=cols.setdefault(p, 'abcefhijklmnpqstuvxyz'[len(cols)%21])
    row+=c
  print('%2d '%y+row)
for p,c in cols.items(): print(c,p)
