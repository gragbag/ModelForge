import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  // Ignore build output and the Python backend (its venv ships bundled JS we
  // must not lint). This is a frontend linter; it should only see frontend code.
  globalIgnores(['dist', 'backend']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // This new rule flags the standard "fetch data on mount" pattern as a
      // synchronous setState in an effect. Our fetching is async (setState runs
      // after an await), so it's a false positive here. Off.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
])
