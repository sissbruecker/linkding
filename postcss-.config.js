const cssnano = require("cssnano");
const postcssImport = require("postcss-import");
const postcssNesting = require("postcss-nesting");

module.exports = {
  plugins: [
    postcssImport,
    postcssNesting,
    cssnano({
      preset: "default",
    }),
  ],
};
