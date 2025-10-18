function qs(sel, ctx=document){return ctx.querySelector(sel)}
function qsa(sel, ctx=document){return Array.from(ctx.querySelectorAll(sel))}

// Map of Osiedle name -> numeric id (example mapping)
const OSIEDLE_MAP = {
  'Winiary': 1,
  'Skarpa': 2,
  'Miodowa': 3,
  'Stare Miasto': 4,
  'Tysiąclecia': 5,
  'Kochanowskiego': 6,
  'Dworcowa': 7,
  'Trzepowo': 8,
  'Łukasiewicza': 9,
  'Kolegialna': 10,
  'Wyszogrodzka': 11,
  'Międzytorze': 12,
  'Podolszyce Pn.': 13,
  'Podolszyce Pd.': 14,
  'Zielony Jar': 15,
  'Borowiczki': 16,
  'Imielnica': 17,
  'Radziwie': 18,
  'Góry': 19,
  'Ciechomice': 20,
  'Pradolina Wisły': 21
};

function setError(input, message){
  let el = input.closest('.field') || input.parentElement;
  let err = el.querySelector('.field-error');
  if(!err){
    err = document.createElement('div');
    err.className = 'field-error';
    el.appendChild(err);
  }
  err.textContent = message;
  input.classList.add('invalid');
}

function clearError(input){
  let el = input.closest('.field') || input.parentElement;
  let err = el.querySelector('.field-error');
  if(err) err.textContent = '';
  input.classList.remove('invalid');
}

function validateNumber(input, opts={min:null, max:null, required:true}){
  clearError(input);
  const v = input.value === '' ? null : Number(input.value);
  if(opts.required && (v === null || Number.isNaN(v))){
    setError(input, 'To pole jest wymagane i musi być liczbą');
    return false;
  }
  if(v !== null){
    if(opts.min !== null && v < opts.min){ setError(input, `Minimalna wartość to ${opts.min}`); return false }
    if(opts.max !== null && v > opts.max){ setError(input, `Maksymalna wartość to ${opts.max}`); return false }
  }
  return true;
}

function validateDate(input, opts={required:false}){
  clearError(input);
  const v = input.value;
  if(opts.required && !v){ setError(input, 'To pole jest wymagane'); return false }
  if(v){
    const d = new Date(v);
    if(Number.isNaN(d.getTime())){ setError(input, 'Nieprawidłowa data'); return false }
  }
  return true;
}

function validateNotes(input, opts={maxLen:256}){
  clearError(input);
  const v = input.value || '';
  if(v.length > opts.maxLen){ setError(input, `Maksymalna długość to ${opts.maxLen} znaków`); return false }
  return true;
}

function validateForm(form){
  let ok = true;
  // Required ids (hidden or visible selects)
  const idEstate = qs('[name="id_estate"]', form);
  if(idEstate && (!idEstate.value || idEstate.value === '')){ setError(idEstate, 'Wybierz nieruchomość'); ok = false }

  // If user selected to add a new estate, validate the address parts
  const newEstateFields = qs('#new_estate_fields');
  if(idEstate && idEstate.value === 'new' && newEstateFields){
    const osiedle = qs('[name="new_est_osiedle"]', form);
    const type = qs('[name="new_est_type"]', form);
    const postal = qs('[name="new_est_postal"]', form);
    const street = qs('[name="new_est_street"]', form);
    const building = qs('[name="new_est_building"]', form);
    const apartment = qs('[name="new_est_apartment"]', form);

    if(osiedle && (!osiedle.value || !(osiedle.value in OSIEDLE_MAP))){ setError(osiedle, 'Wybierz osiedle'); ok = false }
    if(type && (!type.value || (type.value !== 'mieszkanie' && type.value !== 'dom'))){ setError(type, 'Wybierz typ nieruchomości'); ok = false }
    // if type is mieszkanie (apartment), validate attachment presence/size/type
    const attachment = qs('[name="new_est_attachment"]', form);
    if(type && type.value === 'mieszkanie'){
      if(attachment){
        const files = attachment.files;
        if(!files || files.length === 0){ setError(attachment, 'Dołącz zaświadczenie (pdf/jpg/png)'); ok = false }
        else {
          const f = files[0];
          const maxBytes = 10 * 1024 * 1024; // 10 MB
          const allowed = ['application/pdf','image/jpeg','image/jpg','image/png'];
          if(f.size > maxBytes){ setError(attachment, 'Plik nie może być większy niż 10 MB'); ok = false }
          if(f.type && allowed.indexOf(f.type) === -1){ setError(attachment, 'Nieprawidłowy typ pliku (dozwolone: pdf, jpg, png)'); ok = false }
          // If type is missing (some browsers), also validate by extension
          if(!f.type){
            const name = (f.name || '').toLowerCase();
            if(!name.match(/\.pdf$|\.jpe?g$|\.png$/)){
              setError(attachment, 'Nieprawidłowy plik (rozszerzenie)'); ok = false
            }
          }
        }
      }
    }
    if(postal && postal.value){
      if(!/^[0-9]{2}-[0-9]{3}$/.test(postal.value)){ setError(postal, 'Kod pocztowy powinien mieć format 09-400'); ok = false }
    } else { setError(postal, 'Wpisz kod pocztowy'); ok = false }
    if(street && (!street.value || street.value.trim().length < 2)){ setError(street, 'Wpisz nazwę ulicy'); ok = false }
    if(building && (!building.value || building.value.trim().length < 1)){ setError(building, 'Wpisz numer budynku'); ok = false }
    // apartment is optional
  }

  // bag_count removed (not required)

  // dates
  const arrival = qs('[name="bag_arrival_date"]', form);
  const depart = qs('[name="bag_depart_date"]', form);
  if(arrival){ if(!validateDate(arrival, {required:false})) ok = false }
  if(depart){ if(!validateDate(depart, {required:false})) ok = false }
  // if both present, arrival <= depart
  if(arrival && depart && arrival.value && depart.value){
    const a = new Date(arrival.value);
    const d = new Date(depart.value);
    if(a.getTime() > d.getTime()){
      setError(depart, 'Data zakończenia nie może być wcześniejsza niż data rozpoczęcia');
      ok = false;
    }
  }

  // notes length
  const notes = qs('[name="notes"]', form);
  if(notes && !validateNotes(notes)) ok = false;

  return ok;
}


window.addEventListener('load', function(){
  const form = qs('#applicationForm');
  if(!form) return;

  // toggle new estate fields when "Dodaj nową nieruchomość" is selected
  const idEstateSelect = qs('#id_estate', form);
  const newEstateBlock = qs('#new_estate_fields', form);
  if(idEstateSelect && newEstateBlock){
    function toggleNewEstate(){
      if(idEstateSelect.value === 'new'){
        newEstateBlock.style.display = 'block';
      } else {
        // hide and clear values/errors
        newEstateBlock.style.display = 'none';
        qsa('input, textarea', newEstateBlock).forEach(i=>{ i.value = ''; clearError(i); });
      }
    }
    idEstateSelect.addEventListener('change', toggleNewEstate);
    // run once on load
    toggleNewEstate();
  }

  // Toggle attachment visibility when new_est_type changes
  const newType = qs('#new_est_type', form);
  const attachmentField = qs('#new_est_attachment_field', form);
  const attachmentInput = qs('#new_est_attachment', form);
  if(newType && attachmentField){
    function toggleAttachment(){
      if(newType.value === 'mieszkanie'){
        attachmentField.style.display = 'block';
      } else {
        // hide and clear file input + errors
        attachmentField.style.display = 'none';
        if(attachmentInput){ attachmentInput.value = ''; clearError(attachmentInput); }
      }
    }
    newType.addEventListener('change', toggleAttachment);
    // run once on load
    toggleAttachment();
  }

  // Enhance file input: show filename in adjacent span and provide a nice button UX
  const attachmentName = qs('#new_est_attachment_name', form);
  if(attachmentInput && attachmentName){
    // wrap input with a visual button if not already
    const parent = attachmentInput.parentElement;
    if(parent && !parent.classList.contains('file-input-wrap')){
      parent.classList.add('file-input-wrap');
      // create visible button label
      const btn = document.createElement('label');
      btn.className = 'btn-file';
      btn.textContent = 'Załącz plik';
      // ensure clicking label focuses the file input
      btn.htmlFor = attachmentInput.id;
      parent.insertBefore(btn, attachmentInput);
    }

    attachmentInput.addEventListener('change', function(){
      clearError(attachmentInput);
      const f = this.files && this.files[0];
      if(!f){ attachmentName.textContent = ''; return }
      attachmentName.textContent = f.name;
    });
  }

  // clear errors on input
  qsa('#applicationForm input, #applicationForm textarea, #applicationForm select').forEach(el=>{
    el.addEventListener('input', ()=> clearError(el));
  });

  form.addEventListener('submit', function(e){
    e.preventDefault();
    // clear all existing errors first
    qsa('.field-error', form).forEach(el=> el.textContent='');
    qsa('.invalid', form).forEach(el=> el.classList.remove('invalid'));

    if(!validateForm(form)){
      const firstErr = form.querySelector('.field-error:not(:empty)');
      if(firstErr) firstErr.scrollIntoView({behavior:'smooth', block:'center'});
      return false;
    }

    // If valid, show a success message and disable submit to simulate submission (no backend)
    let success = form.querySelector('.form-success');
    if(!success){
      success = document.createElement('div');
      success.className = 'form-success';
      success.textContent = 'Wniosek przygotowany. (Front-end-only demo)';
      form.appendChild(success);
    }
    // optionally, reset the form
    // form.reset();
    return false;
  });
});
