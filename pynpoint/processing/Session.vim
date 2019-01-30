let SessionLoad = 1
let s:so_save = &so | let s:siso_save = &siso | set so=0 siso=0
let v:this_session=expand("<sfile>:p")
silent only
cd /mnt/Documents/ETH/Bluesky/jasper_test_3/lib/python3.6/site-packages/PynPoint/pynpoint/processing
if expand('%') == '' && !&modified && line('$') <= 1 && getline(1) == ''
  let s:wipebuf = bufnr('%')
endif
set shortmess=aoO
badd +3 VisirBurst.py
argglobal
silent! argdel *
$argadd VisirBurst.py
edit VisirBurst.py
set splitbelow splitright
wincmd _ | wincmd |
vsplit
1wincmd h
wincmd w
set nosplitbelow
wincmd t
set winminheight=0
set winheight=1
set winminwidth=0
set winwidth=1
exe 'vert 1resize ' . ((&columns * 185 + 113) / 226)
exe 'vert 2resize ' . ((&columns * 40 + 113) / 226)
argglobal
setlocal fdm=expr
setlocal fde=SimpylFold#FoldExpr(v:lnum)
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=20
setlocal nofen
let s:l = 3 - ((2 * winheight(0) + 27) / 55)
if s:l < 1 | let s:l = 1 | endif
exe s:l
normal! zt
3
normal! 0
lcd /mnt/Documents/ETH/Bluesky/jasper_test_3/lib/python3.6/site-packages/PynPoint/pynpoint/processing
wincmd w
argglobal
enew
file /mnt/Documents/ETH/Bluesky/jasper_test_3/lib/python3.6/site-packages/PynPoint/pynpoint/processing/__Tagbar__.1
setlocal fdm=manual
setlocal fde=0
setlocal fmr={{{,}}}
setlocal fdi=#
setlocal fdl=0
setlocal fml=1
setlocal fdn=20
setlocal nofen
lcd /mnt/Documents/ETH/Bluesky/jasper_test_3/lib/python3.6/site-packages/PynPoint/pynpoint/processing
wincmd w
exe 'vert 1resize ' . ((&columns * 185 + 113) / 226)
exe 'vert 2resize ' . ((&columns * 40 + 113) / 226)
tabnext 1
if exists('s:wipebuf') && getbufvar(s:wipebuf, '&buftype') isnot# 'terminal'
  silent exe 'bwipe ' . s:wipebuf
endif
unlet! s:wipebuf
set winheight=1 winwidth=20 winminheight=1 winminwidth=1 shortmess=filnxToOFatI
let s:sx = expand("<sfile>:p:r")."x.vim"
if file_readable(s:sx)
  exe "source " . fnameescape(s:sx)
endif
let &so = s:so_save | let &siso = s:siso_save
doautoall SessionLoadPost
unlet SessionLoad
" vim: set ft=vim :
