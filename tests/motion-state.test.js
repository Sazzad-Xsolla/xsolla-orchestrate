const assert=require('assert');
const {createMotionTracker}=require('../assets/motion-state.js');
const base=()=>({run_key:'a',approvals:[],workers:[],activity:[],all_done:false});
let passed=0;
function test(name,fn){fn();passed++;console.log('PASS '+name);}
test('initial pending snapshot establishes a quiet baseline',()=>{let t=createMotionTracker(),s=base();s.approvals=[{fingerprint:'one'}];assert.equal(t(s).effect,'none');assert.equal(t(s).effect,'none');assert.equal(t(s).state,'attention');});
test('new and revised requests animate once',()=>{let t=createMotionTracker(),s=base();t(s);s.approvals=[{fingerprint:'one'}];assert.equal(t(s).effect,'attention');assert.equal(t(s).effect,'none');s.approvals=[{fingerprint:'two'}];assert.equal(t(s).effect,'attention');});
test('answered old requests do not replay on reappearance',()=>{let t=createMotionTracker(),s=base();t(s);s.approvals=[{fingerprint:'one'}];t(s);s.approvals=[];t(s);s.approvals=[{fingerprint:'one'}];assert.equal(t(s).effect,'none');});
test('switching runs resets baseline without replay',()=>{let t=createMotionTracker(),s=base();t(s);s.run_key='b';s.all_done=true;assert.equal(t(s).effect,'none');});
test('completion celebrates once',()=>{let t=createMotionTracker(),s=base();t(s);s.all_done=true;assert.equal(t(s).effect,'complete');assert.equal(t(s).effect,'none');});
test('attention takes priority over completion',()=>{let t=createMotionTracker(),s=base();t(s);s.all_done=true;s.approvals=[{fingerprint:'one'}];assert.equal(t(s).effect,'attention');assert.equal(t(s).state,'attention');});
test('new activity animates once',()=>{let t=createMotionTracker(),s=base();t(s);s.activity=[{agent:'a',at:'now',kind:'text',text:'Changed'}];assert.equal(t(s).effect,'log');assert.equal(t(s).effect,'none');});
test('approved agents waiting on Claude are not working',()=>{let t=createMotionTracker(),s=base();s.workers=[{state:'running',awaiting_supervisor:true}];assert.equal(t(s).state,'idle');s.workers[0].awaiting_supervisor=false;assert.equal(t(s).state,'working');});
test('new blocker alerts only once',()=>{let t=createMotionTracker(),s=base();t(s);s.workers=[{id:'a',state:'failed'}];assert.equal(t(s).effect,'attention');assert.equal(t(s).effect,'none');});
console.log(passed+' motion scenarios passed');
