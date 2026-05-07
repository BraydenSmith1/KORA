import React from 'react';
import KoraDemo from './KoraDemo.jsx';

/**
 * Main Application
 *
 * Single-page app that renders the KoraDemo component.
 * KoraDemo handles its own authentication (password gate)
 * and connects to the real Python optimizer via API.
 */
export default function App() {
  return <KoraDemo />;
}
