module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        'background': '#2f3a3f',
        'surface': '#273034',
        'accent': '#455a64',
        'primary': {
          DEFAULT: '#22c55e',
          'hover': '#16a34a',
        },
        'secondary': {
          DEFAULT: '#3b82f6',
          'hover': '#2563eb',
        },
        'text': {
          'primary': '#e0e0e0',
          'secondary': '#b0bec5',
          'light': '#cfd8dc',
        }
      },
    },
  },
  plugins: [],
}
