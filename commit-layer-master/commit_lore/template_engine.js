/**
 * template_engine.js — Template-basierte Prompt-Composition Engine
 * 
 * Supports recursive placeholder substitution: {{VARIABLE}}
 * Designed for LLM-native causal prompt generation
 */

'use strict';

const fs = require('fs');

class TemplateEngine {
  constructor(templatePath = null) {
    this.templates = {};
    this.schema = {};
    
    if (templatePath) {
      this.loadTemplates(templatePath);
    }
  }
  
  /**
   * Load templates from JSON file
   */
  loadTemplates(templatePath) {
    try {
      const data = fs.readFileSync(templatePath, 'utf8');
      this.templates = JSON.parse(data);
      console.log(`[TemplateEngine] Loaded templates from ${templatePath}`);
    } catch (e) {
      console.error(`[TemplateEngine] Failed to load templates from ${templatePath}:`, e.message);
      this.templates = {};
    }
  }
  
  /**
   * Load schema from JSON file
   */
  loadSchema(schemaPath) {
    try {
      const data = fs.readFileSync(schemaPath, 'utf8');
      this.schema = JSON.parse(data);
      console.log(`[TemplateEngine] Loaded schema from ${schemaPath}`);
    } catch (e) {
      console.error(`[TemplateEngine] Failed to load schema from ${schemaPath}:`, e.message);
      this.schema = {};
    }
  }
  
  /**
   * Substitute placeholders in template with variables
   * Supports recursive substitution (placeholders in placeholders)
   */
  substitute(template, variables, options = {}) {
    const {
      maxDepth = 10,
      caseSensitive = false,
      missingBehavior = 'keep_placeholder' // 'keep_placeholder', 'empty', 'error'
    } = options;
    
    let result = template;
    let depth = 0;
    
    while (depth < maxDepth) {
      const before = result;
      
      // Case-insensitive regex if needed (currently template engine always uses 'g' flag)
      result = result.replace(/\{\{(\w+)\}\}/g, (match, key) => {
        const lookupKey = caseSensitive ? key : key.toUpperCase();
        const value = variables[lookupKey];
        
        if (value !== undefined) {
          return String(value);
        }
        
        // Handle missing variables
        switch (missingBehavior) {
        case 'empty':
          return '';
        case 'error':
          throw new Error(`Missing variable: ${lookupKey}`);
        case 'keep_placeholder':
        default:
          return match;
        }
      });
      
      // Stop if no more substitutions occurred
      if (before === result) {
        break;
      }
      
      depth++;
    }
    
    if (depth >= maxDepth) {
      console.warn(`[TemplateEngine] Max recursion depth (${maxDepth}) reached`);
    }
    
    return result;
  }
  
  /**
   * Build narrative prompt from template and causal signals
   */
  buildNarrativePrompt(character, mood, relationship, domain, sequence, codeContext, options = {}) {
    const charTemplate = this.templates.character_templates?.[character];
    
    if (!charTemplate) {
      console.error(`[TemplateEngine] No template found for character: ${character}`);
      return this.fallbackPrompt(character, mood, codeContext);
    }
    
    // Collect all variables
    const variables = this.collectVariables(
      character, mood, relationship, domain, sequence, codeContext, charTemplate
    );
    
    // Substitute template
    const prompt = this.substitute(
      charTemplate.commit_template || charTemplate.base_template,
      variables,
      options
    );
    
    return prompt;
  }
  
  /**
   * Collect all variables for template substitution
   */
  collectVariables(character, mood, relationship, domain, sequence, codeContext, charTemplate) {
    const variables = {};
    
    // Character variables
    variables.NAME = character;
    variables.ROLE = charTemplate.role || 'Unknown';
    variables.VOICE_TRAITS = charTemplate.voice_traits || '';
    
    // Mood variables
    variables.MOOD = mood;
    const moodModifiers = charTemplate.mood_modifiers?.[mood] || {};
    Object.entries(moodModifiers).forEach(([key, value]) => {
      variables[key] = this.substitute(value, variables);
    });
    
    // Set defaults if mood modifiers didn't provide them
    if (!variables.INTRO_PHRASE) {
      variables.INTRO_PHRASE = this.getDefaultIntro(mood);
    }
    if (!variables.OUTCOME_PHRASE) {
      variables.OUTCOME_PHRASE = this.getDefaultOutcome(mood);
    }
    
    // Relationship variables
    variables.PREV_NARRATOR = relationship.prev_narrator || 'keiner';
    variables.RELATIONSHIP_STATE = relationship.state || 'fresh_pair';
    variables.RELATIONSHIP_TEXT = this.getRelationshipText(relationship);
    
    // Domain variables
    variables.DOMAIN = domain.primary || 'Unknown';
    variables.SECONDARY_DOMAIN = domain.secondary || '';
    variables.DOMAIN_RESONANCE = domain.resonance || 'native_domain';
    variables.DOMAIN_TEXT = this.getDomainText(domain);
    
    // Sequence variables
    variables.SEQUENCE_PHASE = sequence.phase || 'arc_mid';
    variables.THEME = sequence.theme || 'general';
    variables.PROGRESS = sequence.progress || 50;
    variables.SEQUENCE_TEXT = this.getSequenceText(sequence);
    
    // Code context variables
    variables.CHANGE_TYPE = codeContext.type || 'feature';
    variables.COMPLEXITY = codeContext.complexity || 'medium';
    variables.FILES = Array.isArray(codeContext.files) ? codeContext.files.join(', ') : codeContext.files || '';
    variables.TECHNICAL_SUMMARY = codeContext.summary || '';
    variables.IMPULSE = codeContext.impulse || '';
    
    // Narrative variables
    variables.TRANSITION_TEXT = this.getTransitionText(relationship);
    variables.OPENING_TEXT = this.getOpeningText(mood, sequence);
    variables.CLOSING_TEXT = this.getClosingText(character, mood);
    
    return variables;
  }
  
  /**
   * Get default intro phrase for mood
   */
  getDefaultIntro(mood) {
    const defaults = {
      sachlich: 'Ausführung:',
      alarmiert: 'DRINGEND:',
      triumphierend: 'Erfolg:',
      erschöpft: 'Nächster Fix:',
      selbstironisch: 'Natürlich:',
      neugierig: 'Interessant:',
      'müde-zufrieden': 'Abschluss:',
      trocken: 'Operation:',
      warm: 'Erledigt:',
      sarkastisch: 'Wie erwartet:'
    };
    return defaults[mood] || 'Status:';
  }
  
  /**
   * Get default outcome phrase for mood
   */
  getDefaultOutcome(mood) {
    const defaults = {
      sachlich: 'Vorgang abgeschlossen.',
      alarmiert: 'Kritischer Fehler behoben.',
      triumphierend: 'Ziel erreicht.',
      erschöpft: 'Erledigt. Weiter.',
      selbstironisch: 'Funktioniert. Trotz allem.',
      neugierig: 'Erkenntnis gesichert.',
      'müde-zufrieden': 'Läuft. Endlich.',
      trocken: 'Exit code: 0.',
      warm: 'Gute Arbeit.',
      sarkastisch: 'Kompiliert. Überraschenderweise.'
    };
    return defaults[mood] || 'Fertig.';
  }
  
  /**
   * Get relationship text
   */
  getRelationshipText(relationship) {
    const templates = this.templates.relationship_templates || {};
    const template = templates[relationship.state] || templates.fresh_pair;
    return this.substitute(template || '{{PREV_NARRATOR}} hat den Task gestartet.', {
      PREV_NARRATOR: relationship.prev_narrator || 'keiner'
    });
  }
  
  /**
   * Get domain text
   */
  getDomainText(domain) {
    const templates = this.templates.domain_templates || {};
    const template = templates[domain.resonance] || templates.native_domain;
    return this.substitute(template || 'Domain: {{DOMAIN}}.', {
      DOMAIN: domain.primary || 'Unknown',
      SECONDARY_DOMAIN: domain.secondary || ''
    });
  }
  
  /**
   * Get sequence text
   */
  getSequenceText(sequence) {
    const templates = this.templates.sequence_templates || {};
    const template = templates[sequence.phase] || templates.arc_mid;
    return this.substitute(template || 'Phase: {{SEQUENCE_PHASE}}.', {
      SEQUENCE_PHASE: sequence.phase,
      THEME: sequence.theme,
      PROGRESS: sequence.progress
    });
  }
  
  /**
   * Get transition text between narrators
   */
  getTransitionText(relationship) {
    if (!relationship.prev_narrator) {
      return '';
    }
    
    const transitions = {
      fresh_pair: `Wo ${relationship.prev_narrator} den Stift niedergelegt hat, setze ich an.`,
      established_duo: `${relationship.prev_narrator} und ich: bewährtes Team.`,
      conflict_pair: `${relationship.prev_narrator} hat wieder eine Theorie. Ich mache Facts.`,
      trusted_team: `${relationship.prev_narrator}s groundwork, meine execution.`
    };
    
    return transitions[relationship.state] || transitions.fresh_pair;
  }
  
  /**
   * Get opening text
   */
  getOpeningText(mood, sequence) {
    if (sequence.phase === 'arc_opening') {
      return `Arc-Start: ${sequence.theme}.`;
    }
    return this.getDefaultIntro(mood);
  }
  
  /**
   * Get closing text
   */
  getClosingText(character, mood) {
    const closings = {
      Buffy: 'Die Strategie ist klar. Nächster Schritt.',
      Basher: 'Funktioniert. Getestet. Weiter geht\'s.',
      Vannon: 'Das war der Plan. Oder auch nicht.',
      Thinker: `Die Analyse zeigt: ${mood}. Konsequenzen werden sich zeigen.`,
      Devin: 'Architektur steht. Sauber.',
      Ghost: `Die Chronik verzeichnet. Datum: ${new Date().toISOString().substring(0, 10)}.`,
      Glitch: 'Verbindung? Zufall? Ich denke nicht.',
      Squizzle: 'Aktenzeichen abgeschlossen. Beweise gesichert.',
      Echo: 'Alles hängt zusammen.',
      Spark: 'Neue Erkenntnis. Spannend!',
      Argos: 'Lokal gelöst. Kein externer Aufwand nötig.',
      Null: `Erledigt. ${mood}.`,
      Flux: 'Und weiter.',
      Sage: 'Die Lektion ist erteilt. Gemerkt.'
    };
    
    return closings[character] || `${character} dokumentiert: ${mood}.`;
  }
  
  /**
   * Fallback prompt if template not found
   */
  fallbackPrompt(character, mood, codeContext) {
    return `${this.getDefaultIntro(mood)} ${character} here. ${codeContext.summary || 'No summary'} ${this.getDefaultOutcome(mood)}`;
  }
  
  /**
   * Validate template syntax
   */
  validateTemplate(template) {
    const errors = [];
    
    // Check for unbalanced braces
    const openCount = (template.match(/\{\{/g) || []).length;
    const closeCount = (template.match(/\}\}/g) || []).length;
    
    if (openCount !== closeCount) {
      errors.push(`Unbalanced braces: ${openCount} open, ${closeCount} close`);
    }
    
    // Check for recursive patterns that might cause infinite loops
    if (/\{\{(\w+)\}\}.*\{\{\1\}\}/.test(template)) {
      errors.push('Potential infinite recursion detected');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
}

module.exports = TemplateEngine;
