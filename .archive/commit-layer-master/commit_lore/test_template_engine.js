/**
 * test_template_engine.js — Unit Tests für Template-Engine
 */

const TemplateEngine = require('./template_engine');
const path = require('path');

const LORE_DIR = __dirname;
const templatePath = path.join(LORE_DIR, 'narrative_templates.json');
const schemaPath = path.join(LORE_DIR, 'template_schema.json');

console.log('=== TEMPLATE-ENGINE UNIT TESTS ===\n');

// Test 1: Basic Substitution
console.log('Test 1: Basic Substitution');
const engine = new TemplateEngine();
engine.loadTemplates(templatePath);

const testVars = {
  NAME: 'Basher',
  ROLE: 'Terminal Bot',
  INTRO_PHRASE: 'Ausführung:',
  OUTCOME_PHRASE: 'exitCode=0',
  TECHNICAL_SUMMARY: 'CSS Fix',
  FILES: 'core/GUI/index.html'
};

const testTemplate = '{{INTRO_PHRASE}} {{NAME}} ({{ROLE}}): {{TECHNICAL_SUMMARY}} {{FILES}} {{OUTCOME_PHRASE}}';
const result1 = engine.substitute(testTemplate, testVars);
console.log('Template:', testTemplate);
console.log('Variables:', JSON.stringify(testVars, null, 2));
console.log('Result:', result1);
console.log('Expected: Ausführung: Basher (Terminal Bot): CSS Fix core/GUI/index.html exitCode=0');
console.log('Pass:', result1 === 'Ausführung: Basher (Terminal Bot): CSS Fix core/GUI/index.html exitCode=0' ? '✅' : '❌');
console.log();

// Test 2: Recursive Substitution
console.log('Test 2: Recursive Substitution');
const recursiveVars = {
  NAME: 'Buffy',
  GREETING: 'Hello {{NAME}}',
  MESSAGE: '{{GREETING}} World'
};

const recursiveTemplate = '{{MESSAGE}}';
const result2 = engine.substitute(recursiveTemplate, recursiveVars);
console.log('Template:', recursiveTemplate);
console.log('Variables:', JSON.stringify(recursiveVars, null, 2));
console.log('Result:', result2);
console.log('Expected: Hello Buffy World');
console.log('Pass:', result2 === 'Hello Buffy World' ? '✅' : '❌');
console.log();

// Test 3: Missing Variable Handling
console.log('Test 3: Missing Variable Handling (keep_placeholder)');
const incompleteVars = {
  NAME: 'Basher',
  INTRO_PHRASE: 'Test:'
};

const incompleteTemplate = '{{INTRO_PHRASE}} {{NAME}} {{MISSING_VAR}}';
const result3 = engine.substitute(incompleteTemplate, incompleteVars, { missingBehavior: 'keep_placeholder' });
console.log('Template:', incompleteTemplate);
console.log('Variables:', JSON.stringify(incompleteVars, null, 2));
console.log('Result:', result3);
console.log('Expected: Test: Basher {{MISSING_VAR}}');
console.log('Pass:', result3 === 'Test: Basher {{MISSING_VAR}}' ? '✅' : '❌');
console.log();

// Test 4: Case Insensitive Substitution
console.log('Test 4: Case Insensitive Substitution');
const caseVars = {
  NAME: 'Basher'
};

const caseTemplate = '{{name}} {{NAME}} {{Name}}';
const result4 = engine.substitute(caseTemplate, caseVars, { caseSensitive: false });
console.log('Template:', caseTemplate);
console.log('Variables:', JSON.stringify(caseVars, null, 2));
console.log('Result:', result4);
console.log('Expected: Basher Basher Basher');
console.log('Pass:', result4 === 'Basher Basher Basher' ? '✅' : '❌');
console.log();

// Test 5: Full Narrative Prompt Generation
console.log('Test 5: Full Narrative Prompt Generation');
engine.loadSchema(schemaPath);

const causalSignals = {
  character: 'Basher',
  mood: 'sachlich',
  relationship: {
    prev_narrator: 'Buffy',
    state: 'fresh_pair'
  },
  domain: {
    primary: 'GUI',
    secondary: null,
    resonance: 'native_domain'
  },
  sequence: {
    phase: 'arc_mid',
    theme: 'bug_hunt',
    progress: 50
  },
  codeContext: {
    type: 'bugfix',
    complexity: 'low',
    files: ['core/GUI/index.html'],
    summary: 'CSS Fix für Terminal-Tab',
    impulse: 'CSS Fix'
  }
};

try {
  const result5 = engine.buildNarrativePrompt(
    causalSignals.character,
    causalSignals.mood,
    causalSignals.relationship,
    causalSignals.domain,
    causalSignals.sequence,
    causalSignals.codeContext
  );
  console.log('Causal Signals:', JSON.stringify(causalSignals, null, 2));
  console.log('Result:', result5);
  console.log('Pass:', result5.length > 0 ? '✅' : '❌');
} catch (e) {
  console.log('Error:', e.message);
  console.log('Pass: ❌');
}
console.log();

// Test 6: Different Character
console.log('Test 6: Different Character (Buffy)');

const causalSignalsBuffy = {
  character: 'Buffy',
  mood: 'triumphierend',
  relationship: {
    prev_narrator: 'Basher',
    state: 'established_duo'
  },
  domain: {
    primary: 'Architecture',
    secondary: 'GUI',
    resonance: 'native_domain'
  },
  sequence: {
    phase: 'arc_climax',
    theme: 'architecture_triumph',
    progress: 90
  },
  codeContext: {
    type: 'refactor',
    complexity: 'high',
    files: ['core/commit-layer/template_engine.js', 'core/commit-layer/narrative_templates.json'],
    summary: 'Template-Engine Implementierung',
    impulse: 'Template System'
  }
};

try {
  const result6 = engine.buildNarrativePrompt(
    causalSignalsBuffy.character,
    causalSignalsBuffy.mood,
    causalSignalsBuffy.relationship,
    causalSignalsBuffy.domain,
    causalSignalsBuffy.sequence,
    causalSignalsBuffy.codeContext
  );
  console.log('Causal Signals:', JSON.stringify(causalSignalsBuffy, null, 2));
  console.log('Result:', result6);
  console.log('Pass:', result6.length > 0 ? '✅' : '❌');
} catch (e) {
  console.log('Error:', e.message);
  console.log('Pass: ❌');
}
console.log();

console.log('=== TESTS COMPLETE ===');
