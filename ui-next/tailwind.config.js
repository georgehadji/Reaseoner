/** @type {import('tailwindcss').Config} */
const plugin = require('tailwindcss/plugin');

module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'mds-color-hcp-brand': '#000000',
        'mds-color-dark-charcoal': '#15181e',
        'mds-color-near-black': '#0d0e12',
        'mds-color-light-gray': '#f1f2f3',
        'mds-color-mid-gray': '#d5d7db',
        'mds-color-cool-gray': '#b2b6bd',
        'mds-color-dark-gray': '#656a76',
        'mds-color-charcoal': '#3b3d45',
        'mds-color-near-white': '#efeff1',
        'mds-color-terraform-button-background': '#7b42bc',
        'mds-color-vault-button-background': '#ffcf25',
        'mds-color-waypoint-button-background-focus': '#14c6cb',
        'mds-color-waypoint-button-background-hover': '#12b6bb',
        'mds-color-vagrant-brand': '#1868f2',
        'mds-color-palette-purple-300': '#911ced',
        'mds-color-foreground-action-visited': '#a737ff',
        'mds-color-action-blue': '#1060ff',
        'mds-color-link-blue': '#2264d6',
        'mds-color-bright-blue': '#2b89ff',
        'mds-color-palette-amber-200': '#bb5a00',
        'mds-color-palette-amber-100': '#fbeabf',
        'mds-color-vault-radar-gradient-faint-stop': '#fff9cf',
        'mds-color-unified-core-orange-6': '#a9722e',
        'mds-color-unified-core-red-7': '#731e25',
        'mds-color-unified-core-blue-7': '#101a59',
        'mds-color-focus-action-external': 'var(--mds-color-focus-action-external)',
      },
      fontFamily: {
        hashicorpSans: ['__hashicorpSans_96f0ca', '__hashicorpSans_Fallback_96f0ca', 'sans-serif'],
        systemUi: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
      },
      fontSize: {
        'display-hero': ['82px', { lineHeight: '1.17', fontWeight: '600', letterSpacing: 'normal' }],
        'section-heading': ['52px', { lineHeight: '1.19', fontWeight: '600', letterSpacing: 'normal' }],
        'feature-heading': ['42px', { lineHeight: '1.19', fontWeight: '700', letterSpacing: '-0.42px' }],
        'sub-heading': ['34px', { lineHeight: '1.18', fontWeight: '600', letterSpacing: 'normal' }],
        'card-title': ['26px', { lineHeight: '1.19', fontWeight: '700', letterSpacing: 'normal' }],
        'small-title': ['19px', { lineHeight: '1.21', fontWeight: '700', letterSpacing: 'normal' }],
        'body-emphasis': ['17px', { lineHeight: '1.18', fontWeight: '600', letterSpacing: 'normal' }],
        'body-lg': ['20px', { lineHeight: '1.50', fontWeight: '400', letterSpacing: 'normal' }],
        'body': ['16px', { lineHeight: '1.63', fontWeight: '400', letterSpacing: 'normal' }],
        'nav-link': ['15px', { lineHeight: '1.60', fontWeight: '500', letterSpacing: 'normal' }],
        'sm-body': ['14px', { lineHeight: '1.29', fontWeight: '400', letterSpacing: 'normal' }],
        'caption': ['13px', { lineHeight: '1.23', fontWeight: '400', letterSpacing: 'normal' }],
        'uppercase-label': ['13px', { lineHeight: '1.69', fontWeight: '600', letterSpacing: '1.3px' }],
      },
      spacing: {
        '2px': '2px',
        '3px': '3px',
        '4px': '4px',
        '6px': '6px',
        '7px': '7px',
        '8px': '8px',
        '9px': '9px',
        '11px': '11px',
        '12px': '12px',
        '16px': '16px',
        '20px': '20px',
        '24px': '24px',
        '32px': '32px',
        '40px': '40px',
        '48px': '48px',
      },
      borderRadius: {
        '2px': '2px',
        '3px': '3px',
        '4px': '4px',
        '5px': '5px',
        '8px': '8px',
      },
      boxShadow: {
        'micro-shadow': 'rgba(97, 104, 117, 0.05) 0px 1px 1px, rgba(97, 104, 117, 0.05) 0px 2px 2px',
      },
    },
  },
  plugins: [
    plugin(function({ addUtilities }) {
      addUtilities({
        '.font-hashicorp-kern': {
          fontFeatureSettings: '"kern" on',
        },
      });
    }),
  ],
};
