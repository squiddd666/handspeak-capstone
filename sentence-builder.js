// Text composition only. These helpers do not translate ASL grammar.
export function appendWord(message, word) {
  const clean = word.trim().replace(/\s+/g, ' ');
  if (!clean) return message;
  const next = `${message.trimEnd()} ${clean}`.trimStart();
  return next.length <= 1000 ? next : null;
}
export function finishSentence(message, punctuation = '.') {
  if (!['.', '?', '!'].includes(punctuation)) return message;
  const clean = message.trimEnd();
  if (!clean) return message;
  const next = clean.replace(/[.!?]+$/, '') + punctuation;
  return next.length <= 1000 ? next : null;
}
export function removeLastWord(message) {
  return message.trimEnd().replace(/\S+\s*$/, '').trimEnd();
}
