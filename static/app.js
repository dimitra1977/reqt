async function apiGet(path){
  const res = await fetch(path);
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiPost(path, body){
  const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}
async function apiPut(path, body){
  const res = await fetch(path, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}
async function apiDelete(path){
  const res = await fetch(path, {method:'DELETE'});
  if(!res.ok) throw new Error(await res.text());
  return res;
}

let requirements = [];
let selectedId = null;
let parentLookup = {};

function setStatus(text){ document.getElementById('status').textContent = text; }

function buildTree(rows){
  const byParent = {};
  rows.forEach(r=>{ const p = r.parent_requirement_id || ''; (byParent[p] ||= []).push(r); });
  function makeList(parentId){
    const ul = document.createElement('ul');
    (byParent[parentId]||[]).sort((a,b)=> a.level - b.level || a.summary.localeCompare(b.summary)).forEach(r=>{
      const li = document.createElement('li');
      li.textContent = `[${levelLabel(r.level)}] ${r.summary}`;
      li.dataset.id = r.id;
      li.onclick = (e)=>{ e.stopPropagation(); onSelectRequirement(r.id); };
      const children = makeList(r.id);
      if(children.children.length) li.appendChild(children);
      ul.appendChild(li);
    });
    return ul;
  }
  return makeList('');
}

function levelLabel(level){
  return ['Feature','User Story','System Requirement','Sub-System / Interface Requirement','Software / Hardware Requirement'][level]||level;
}

async function refresh(search=''){
  try{
    const rows = await apiGet('/api/requirements' + (search?('?q='+encodeURIComponent(search)):'') );
    requirements = rows;
    const tree = buildTree(rows);
    const container = document.getElementById('requirementsTree');
    container.innerHTML = '';
    container.appendChild(tree);

    const parents = await apiGet('/api/parents');
    parentLookup = {};
    const parentSelect = document.getElementById('parent');
    parentSelect.innerHTML = '';
    const emptyOpt = document.createElement('option'); emptyOpt.value=''; emptyOpt.textContent='(none)'; parentSelect.appendChild(emptyOpt);
    parents.forEach(p=>{ parentLookup[p.id]=p.label; const opt = document.createElement('option'); opt.value=p.id; opt.textContent=p.label; parentSelect.appendChild(opt); });

    setStatus(`Loaded ${rows.length} requirements`);
  }catch(err){ setStatus('Error: '+err.message); }
}

async function onSelectRequirement(id){
  try{
    const r = await apiGet('/api/requirements/'+id);
    selectedId = r.id;
    document.getElementById('summary').value = r.summary||'';
    document.getElementById('description').value = r.description||'';
    document.getElementById('level').value = r.level||0;
    document.getElementById('parent').value = r.parent_requirement_id||'';
    document.getElementById('custom_field_1').value = r.custom_field_1||'';
    document.getElementById('custom_field_2').value = r.custom_field_2||'';
    document.getElementById('custom_field_3').value = r.custom_field_3||'';
    document.getElementById('custom_field_4').value = r.custom_field_4||'';
    setStatus(`Selected ${r.id.slice(0,8)}`);
  }catch(err){ setStatus('Error: '+err.message); }
}

function clearForm(){
  selectedId = null;
  document.getElementById('summary').value='';
  document.getElementById('description').value='';
  document.getElementById('level').value='0';
  document.getElementById('parent').value='';
  document.getElementById('custom_field_1').value='';
  document.getElementById('custom_field_2').value='';
  document.getElementById('custom_field_3').value='';
  document.getElementById('custom_field_4').value='';
}

async function save(){
  const payload = {
    summary: document.getElementById('summary').value.trim(),
    description: document.getElementById('description').value,
    level: parseInt(document.getElementById('level').value||0),
    parent_requirement_id: document.getElementById('parent').value||null,
    custom_field_1: document.getElementById('custom_field_1').value,
    custom_field_2: document.getElementById('custom_field_2').value,
    custom_field_3: document.getElementById('custom_field_3').value,
    custom_field_4: document.getElementById('custom_field_4').value,
  };
  if(!payload.summary){ setStatus('Summary required'); return; }
  try{
    if(selectedId){
      await apiPut('/api/requirements/'+selectedId, payload);
      setStatus('Requirement updated');
    }else{
      const created = await apiPost('/api/requirements', payload);
      selectedId = created.id;
      setStatus('Requirement created');
    }
    await refresh(document.getElementById('searchInput').value.trim());
  }catch(err){ setStatus('Error: '+err.message); }
}

async function remove(){
  if(!selectedId){ setStatus('Select a requirement to delete'); return; }
  if(!confirm('Delete this requirement and its links?')) return;
  try{
    await apiDelete('/api/requirements/'+selectedId);
    setStatus('Requirement deleted');
    clearForm();
    await refresh(document.getElementById('searchInput').value.trim());
  }catch(err){ setStatus('Error: '+err.message); }
}

function createRoot(){ clearForm(); document.getElementById('level').value='0'; setStatus('Creating new root requirement'); }
async function createChild(){
  if(!selectedId){ alert('Select a parent requirement in the tree first.'); return; }
  const parent = await apiGet('/api/requirements/'+selectedId);
  clearForm();
  document.getElementById('level').value = Math.min((parent.level||0)+1,4);
  document.getElementById('parent').value = parent.id;
  setStatus('Creating new child for '+parent.summary);
}

document.addEventListener('DOMContentLoaded', ()=>{
  document.getElementById('searchBtn').onclick = ()=> refresh(document.getElementById('searchInput').value.trim());
  document.getElementById('clearBtn').onclick = ()=>{ document.getElementById('searchInput').value=''; refresh(''); };
  document.getElementById('saveBtn').onclick = save;
  document.getElementById('deleteBtn').onclick = remove;
  document.getElementById('newRootBtn').onclick = createRoot;
  document.getElementById('newChildBtn').onclick = createChild;
  refresh();
});
