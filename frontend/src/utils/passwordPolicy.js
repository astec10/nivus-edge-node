export function meetsPasswordPolicy(value) {
  return value.length >= 8 &&
    value.length <= 256 &&
    Array.from(value).some(character => character.toLowerCase() !== character.toUpperCase()) &&
    /[0-9]/.test(value);
}
