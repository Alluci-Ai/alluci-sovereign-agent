// A toLowerCase function that matches the "C" locale
export const toLowerCaseCLocale = (str: string) => {
  let lower = "";

  for (let i = 0; i < str.length; i++) {
    const charCode = str.charCodeAt(i);
    const char = str.charAt(i);

    if (charCode < 128) {
      lower += char.toLowerCase();
    } else lower += char;
  }

  return lower;
}