export function cycleMarker(month){if(!/^20\d\d-(?:0[1-9]|1[0-2])$/.test(month))throw Error("Invalid month");return "<!-- guardian-monthly:"+month+" -->";}
export function shouldRunMonthly({event,month,comments=[]}){if(event!=="schedule")return true;const marker=cycleMarker(month);return !comments.some(c=>typeof(c?.body??c)==="string"&&String(c.body??c).includes(marker));}
