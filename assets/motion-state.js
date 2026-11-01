/* Pure transition tracking: polling is not a notification event. */
function createMotionTracker() {
  let run=null,initialized=false,complete=false,seen=new Set(),events=new Set();
  const eventKey=e=>JSON.stringify([e.agent,e.at,e.kind,e.text,e.sequence]);
  return function observe(snapshot) {
    const key=snapshot.run_key || snapshot.run_id || 'snapshot';
    const attention=[...(snapshot.approvals||[]).map(a=>'request:'+a.fingerprint),...(snapshot.workers||[]).filter(w=>['blocked','paused','failed'].includes(w.state)).map(w=>'worker:'+w.id+':'+w.state+':'+(w.watchdog||''))];
    const activity=(snapshot.activity||[]).map(eventKey);
    let effect='none',fresh=[];
    if(initialized&&key===run){
      fresh=activity.filter(k=>!events.has(k));
      if(attention.some(k=>!seen.has(k)))effect='attention';
      else if(!complete&&snapshot.all_done&&!attention.length)effect='complete';
      else if(fresh.length)effect='log';
    } else {seen=new Set();events=new Set();}
    attention.forEach(k=>seen.add(k));activity.forEach(k=>events.add(k));
    if(events.size>1000)events=new Set(activity);
    run=key;initialized=true;complete=!!snapshot.all_done;
    const active=(snapshot.workers||[]).some(w=>['running','dispatching'].includes(w.state)&&!w.awaiting_approval&&!w.awaiting_supervisor);
    return {effect,fresh,state:attention.length?'attention':snapshot.all_done?'complete':active?'working':'idle'};
  };
}
if(typeof module!=='undefined')module.exports={createMotionTracker};
