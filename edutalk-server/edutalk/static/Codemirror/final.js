function panestwoed(cm, line, gutter) {
  var state = cm.state.foldGutter;
  if (!state) return;
  var opts = state.options;
  if (gutter != opts.gutter) return;
  var folded = isFolded(dv.rightOriginal(), line);
  if (folded) folded.clear();
  else dv.rightOriginal().foldCode(Pos(line, 0), opts.rangeFinder);
}