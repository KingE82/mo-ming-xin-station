# -*- coding: utf-8 -*-
"""mdRender 前端渲染器（单一来源：app.py 与 daogui_lib 共用）"""

MD_RENDER_JS = """
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 引用块 ====
    if(/^\s*&gt;/.test(l) || /^\s*>\s?/.test(l)){
      var q = [l.replace(/^\s*>\s?/, '')];
      while(i+1 < lines.length && (/^\s*>\s?/.test(lines[i+1]) || /^\s*&gt;/.test(lines[i+1]))){
        i++; q.push(lines[i].replace(/^\s*>\s?/, '').replace(/^\s*&gt;/, ''));
      }
      closeList();
      html += '<blockquote style="margin:8px 0;padding:8px 12px;background:#faf5f0;border-left:3px solid #b8453a;color:#555;border-radius:0 8px 8px 0">' + q.map(function(x){return mdInline(x.trim())}).join('<br>') + '</blockquote>';
      continue;
    }
    // ==== 分隔线 ====
    if(/^\s*([-*_])\s*\\1\s*\\1+\s*$/.test(l)){ closeList(); html += '<hr style="border:none;border-top:1px dashed #e0d8d2;margin:16px 0">'; continue; }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}
"""
