const nextJest = require('next/jest');

const createJestConfig = nextJest({ dir: './' });

/** @type {import('jest').Config} */
const customJestConfig = {
  setupFilesAfterSetup: ['<rootDir>/src/test-setup.ts'],
  testEnvironment: 'jsdom',
};

module.exports = createJestConfig(customJestConfig);
