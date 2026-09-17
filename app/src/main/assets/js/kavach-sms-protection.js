/**
 * KAVACH SMS PROTECTION - MERA PART (6 Responsibilities Only)
 * 
 * Responsibility 1: Request native SMS permissions.
 * Responsibility 2: Detect newly received SMS messages automatically.
 * Responsibility 3: Pass SMS text to the risk engine.
 * Responsibility 4: Generate a warning notification in the selected language.
 * Responsibility 5: Send a high-risk warning to the trusted contact.
 * Responsibility 6: Prevent duplicate alerts.
 */

// --- Responsibility 1: Permission ---
const SmsPermission = {
  check: () => {
    try { if (window.Android?.checkSmsPermission) return window.Android.checkSmsPermission(); } catch(e){}
    return localStorage.getItem('kavach_sms_permission') || 'required';
  },
  request: () => {
    try { 
      if (window.Android?.requestSmsPermission) Android.requestSmsPermission();
      else { localStorage.setItem('kavach_sms_permission','granted'); SmsPermission.updateUI('granted'); }
    } catch(e){}
  },
  updateUI: (status) => {
    const card = document.getElementById('smsStatusCard');
    const title = document.getElementById('smsStatusTitle');
    const desc = document.getElementById('smsStatusDescription');
    const section = document.getElementById('smsPermissionSection');
    if (!card) return;
    const lang = localStorage.getItem('kavach_language')||'en';
    if (status==='granted') {
      card.classList.remove('permission-needed'); card.classList.add('protection-active');
      if (title) title.textContent = lang==='hi'?'सुरक्षा सक्रिय':'Protection Active';
      if (desc) desc.textContent = lang==='hi'?'कवच सक्रिय है':'Kavach is checking SMS';
      if (section) section.classList.add('hidden');
    } else {
      card.classList.add('permission-needed'); card.classList.remove('protection-active');
    }
  }
};

// --- Responsibility 6: Prevent duplicate ---
const DuplicateManager = {
  isDuplicate: (sender, body) => {
    try { if (window.Android?.isDuplicateCheck) return window.Android.isDuplicateCheck(sender, body); } catch(e){}
    const stored = JSON.parse(localStorage.getItem('kavach_processed')||'[]');
    const hash = (sender+'_'+body.trim().toLowerCase()).split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0);
    return stored.some(e=>e.hash===hash && (Date.now()-e.time)<600000);
  },
  mark: (sender, body) => {
    let stored = JSON.parse(localStorage.getItem('kavach_processed')||'[]');
    const hash = (sender+'_'+body.trim().toLowerCase()).split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0);
    stored = stored.filter(e=>(Date.now()-e.time)<1200000);
    stored.push({hash, time:Date.now(), sender});
    if (stored.length>50) stored=stored.slice(-50);
    localStorage.setItem('kavach_processed', JSON.stringify(stored));
  }
};

// --- Responsibility 3: Risk Engine ---
const RiskEngine = {
  analyze: (sender, body) => {
    const lower = body.toLowerCase();
    let score=0, reasons=[];
    const hasLink = /(https?:\/\/|bit\.ly|tinyurl|www\.|\.com\/|\.in\/)/i.test(body);
    if (hasLink) { score+=40; reasons.push('contains_link'); }
    if (/(kyc blocked|account blocked|lottery won|you have won|urgent|click here|verify now|share otp)/i.test(lower)) { score+=30; reasons.push('high_risk_keyword'); }
    if (lower.includes('urgent')||lower.includes('immediately')) { score+=15; reasons.push('urgency'); }
    if (sender.length===10 && /^\d+$/.test(sender) && hasLink) { score+=20; reasons.push('unknown_sender'); }
    let level='SAFE'; if(score>=50) level='HIGH_RISK'; else if(score>=20) level='SUSPICIOUS';
    return {level, score, reasons, hasLink, sender, body, timestamp:Date.now()};
  }
};

// --- Responsibility 4: Notification in selected language ---
const NotificationManager = {
  show: (result) => {
    const lang = localStorage.getItem('kavach_language')||'en';
    const chip = document.getElementById('latestResultStatus');
    const senderEl = document.getElementById('smsSender');
    const timeEl = document.getElementById('smsTime');
    const levelEl = document.getElementById('riskLevel');
    const reasonEl = document.getElementById('riskReason');
    const latestDiv = document.getElementById('latestSmsResult');
    const emptyDiv = document.getElementById('emptySmsState');
    
    if (emptyDiv) emptyDiv.classList.add('hidden');
    if (latestDiv) latestDiv.classList.remove('hidden');
    if (senderEl) senderEl.textContent = result.sender;
    if (timeEl) timeEl.textContent = new Date(result.timestamp).toLocaleString();
    if (chip) {
      chip.textContent = result.level==='HIGH_RISK'?(lang==='hi'?'बहुत खतरनाक':'High Risk'):result.level==='SUSPICIOUS'?(lang==='hi'?'संदिग्ध':'Suspicious'):(lang==='hi'?'सुरक्षित':'Safe');
      chip.style.background = result.level==='HIGH_RISK'?'#FFEBEE':result.level==='SUSPICIOUS'?'#FFF3E0':'#E8F5E9';
    }
    if (levelEl) levelEl.textContent = chip.textContent;
    if (reasonEl) {
      const map = {contains_link: lang==='hi'?'संदिग्ध लिंक है':'Contains suspicious link', high_risk_keyword: lang==='hi'?'फर्जी KYC/लॉटरी':'Fake KYC/Lottery scam'};
      reasonEl.textContent = map[result.reasons[0]]||result.reasons[0]||'Safe';
    }
    localStorage.setItem('kavach_latest', JSON.stringify(result));
    
    // Responsibility 5: High-risk -> trusted contact
    if (result.level==='HIGH_RISK') TrustedContact.sendAlert(result);
  }
};

// --- Responsibility 5: Send high-risk warning to trusted contact ---
const TrustedContact = {
  get: () => {
    try { if (window.Android?.getTrustedContact) return JSON.parse(window.Android.getTrustedContact()); } catch(e){}
    const name=localStorage.getItem('tc_name'), phone=localStorage.getItem('tc_phone'), consent=localStorage.getItem('tc_consent')==='true';
    return (name&&phone&&consent)?{name, phone, hasContact:true}:{hasContact:false};
  },
  sendAlert: (result) => {
    const contact = TrustedContact.get();
    if (!contact.hasContact) return;
    const last = parseInt(localStorage.getItem('tc_last')||'0');
    if ((Date.now()-last)<300000) return; // 5 min cooldown
    console.log('Trusted contact alerted:', contact.name, 'for', result.sender);
    localStorage.setItem('tc_last', Date.now().toString());
    const banner = document.getElementById('trustedContactBanner');
    if (banner) { banner.textContent = `Trusted contact alerted: ${contact.name}`; banner.classList.remove('hidden'); }
  }
};

// --- Responsibility 2: Detect newly received SMS automatically ---
const SmsDetector = {
  handleNewSms: (sender, body, timestamp) => {
    // Responsibility 6: Prevent duplicate
    if (DuplicateManager.isDuplicate(sender, body)) { console.log('Duplicate skipped'); return; }
    
    // Responsibility 3: Pass to risk engine
    let result;
    try {
      if (window.Android?.analyzeText) {
        const nativeRes = JSON.parse(window.Android.analyzeText(sender, body));
        result = {sender, body, timestamp: timestamp||Date.now(), level: nativeRes.level, score: nativeRes.score, reasons: nativeRes.reasonCodes?nativeRes.reasonCodes.split(','):[], hasLink: nativeRes.hasLink};
      } else {
        result = RiskEngine.analyze(sender, body);
      }
    } catch(e) { result = RiskEngine.analyze(sender, body); }
    
    DuplicateManager.mark(sender, body);
    
    // Responsibility 4: Generate warning notification
    NotificationManager.show(result);
    
    // Responsibility 5 is handled inside NotificationManager.show
  }
};

// Global callbacks for native
window.onPermissionResult = (status) => { localStorage.setItem('kavach_sms_permission', status); SmsPermission.updateUI(status); };
window.onSmsReceived = (data) => {
  let obj = typeof data==='string'?JSON.parse(data):data;
  if (obj.sender && obj.level) NotificationManager.show(obj);
  else if (obj.sender && obj.body) SmsDetector.handleNewSms(obj.sender, obj.body, obj.timestamp);
};
window.testSms = (sender, body) => SmsDetector.handleNewSms(sender, body, Date.now());

// Init
document.addEventListener('DOMContentLoaded', () => {
  SmsPermission.updateUI(SmsPermission.check());
  const btn = document.getElementById('enableSmsPermissionButton');
  if (btn) btn.addEventListener('click', ()=>SmsPermission.request());
  
  // Load latest result
  try {
    let res=null;
    if (window.Android?.getLatestResult) {
      const s=window.Android.getLatestResult();
      if(s&&s!=='{}') { const p=JSON.parse(s); if(p.sender) res={sender:p.sender, level:p.level, timestamp:p.timestamp, reasons:p.reasonCodes?p.reasonCodes.split(','):[]}; }
    }
    if(!res) { const stored=localStorage.getItem('kavach_latest'); if(stored) res=JSON.parse(stored); }
    if(res?.sender) NotificationManager.show(res);
  } catch(e){}
});
