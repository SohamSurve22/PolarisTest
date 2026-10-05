import React, { useState } from "react";
import "./LandingPage.css";

export default function LandingPage({ onExplore, onLogin }) {
  const [activeFaq, setActiveFaq] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedGraphNode, setSelectedGraphNode] = useState("dpdp");
  const [heroHoverNode, setHeroHoverNode] = useState(null);
  const [reasonStep, setReasonStep] = useState(0);

  const toggleFaq = (index) => {
    setActiveFaq(activeFaq === index ? null : index);
  };

  // Node details for Hero interactive visual
  const heroNodeInfo = {
    reg: { title: "Regulation Node", detail: "DPDP Act (2023) — Section 6: Data Fiduciary Obligations" },
    req: { title: "Requirement Node", detail: "Explicit consent notice required prior to processing personal data" },
    clause: { title: "Policy Clause", detail: "Privacy Policy Sec 4.1: 'We collect data upon explicit user opt-in'" },
    evidence: { title: "Compliance Evidence", detail: "Verified match: User consent modal snippet + timestamp logs" },
    status: { title: "Compliance Status", detail: "COVERED — 96% confidence score via GraphRAG traversal" },
  };

  // Node data for Section 3 Knowledge Graph
  const graphNodes = {
    dpdp: {
      id: "dpdp",
      name: "DPDP Act 2023",
      category: "Regulation",
      connections: ["consent", "retention", "notice", "fiduciary"],
      desc: "Digital Personal Data Protection Act — Primary Indian data privacy legislation.",
    },
    itact: {
      id: "itact",
      name: "IT Act 2000",
      category: "Regulation",
      connections: ["security", "certin", "spdi"],
      desc: "Information Technology Act — Governs electronic commerce and cybercrime in India.",
    },
    spdi: {
      id: "spdi",
      name: "SPDI Rules 2011",
      category: "Regulation",
      connections: ["security", "sensitive", "consent"],
      desc: "Sensitive Personal Data or Information Rules under IT Act Section 43A.",
    },
    certin: {
      id: "certin",
      name: "CERT-In Directions",
      category: "Regulation",
      connections: ["security", "incident"],
      desc: "Cybersecurity Directions for reporting cyber safety incidents within 6 hours.",
    },
    consent: {
      id: "consent",
      name: "Consent Obligation",
      category: "Requirement",
      connections: ["dpdp", "spdi", "clause4"],
      desc: "Mandates clear, itemized, and withdrawable consent prior to data collection.",
    },
    security: {
      id: "security",
      name: "Security Safeguards",
      category: "Requirement",
      connections: ["itact", "certin", "spdi", "clause8"],
      desc: "Requires technical & organizational measures to protect personal data.",
    },
    retention: {
      id: "retention",
      name: "Data Retention",
      category: "Requirement",
      connections: ["dpdp", "clause6"],
      desc: "Data must be erased as soon as the purpose of processing is fulfilled.",
    },
    clause4: {
      id: "clause4",
      name: "Clause 4.1 (Consent)",
      category: "Policy Clause",
      connections: ["consent", "evidence1"],
      desc: "'Users may choose to grant or revoke consent at any time via settings.'",
    },
    clause8: {
      id: "clause8",
      name: "Clause 8.3 (Security)",
      category: "Policy Clause",
      connections: ["security", "evidence2"],
      desc: "'All sensitive data is encrypted at rest using AES-256 standards.'",
    },
    clause6: {
      id: "clause6",
      name: "Clause 6.2 (Retention)",
      category: "Policy Clause",
      connections: ["retention"],
      desc: "'Account data is retained for 3 years after account termination.' (Partial Gap)",
    },
    evidence1: {
      id: "evidence1",
      name: "Consent UI Log",
      category: "Evidence",
      connections: ["clause4"],
      desc: "Verified UI component screenshot & event log for consent withdrawal.",
    },
    evidence2: {
      id: "evidence2",
      name: "Encryption Cert",
      category: "Evidence",
      connections: ["clause8"],
      desc: "KMS Key Configuration & Third-party SOC2 Security Audit Report.",
    },
  };

  const faqList = [
    {
      q: "What is PolarisLex?",
      a: "PolarisLex is a compliance intelligence platform built on knowledge graphs and GraphRAG. It analyzes privacy policies against Indian data-protection and cybersecurity mandates by converting complex regulations, requirements, policy clauses, and evidence into an interconnected, explainable compliance map.",
    },
    {
      q: "What regulations does PolarisLex currently cover?",
      a: "PolarisLex focuses primarily on Indian privacy and cybersecurity frameworks, including the Digital Personal Data Protection (DPDP) Act 2023, Information Technology Act 2000, SPDI Rules 2011, and CERT-In Cyber Security Directions 2022.",
    },
    {
      q: "How is PolarisLex different from keyword-based compliance checking?",
      a: "Traditional tools rely on simple keyword similarity or basic document search, which misses contextual relationships and legal logic. PolarisLex maps regulations to specific legal obligations, entities, policy clauses, and evidence as a knowledge graph, enabling structural gap analysis and multi-hop reasoning.",
    },
    {
      q: "What is GraphRAG?",
      a: "GraphRAG (Graph-Augmented Retrieval Generation) combines vector similarity search with knowledge graph traversal. Instead of retrieving isolated text snippets, GraphRAG retrieves connected subgraphs containing the exact legal requirements, related definitions, and corresponding policy evidence.",
    },
    {
      q: "Can PolarisLex explain why a requirement was considered covered or missing?",
      a: "Yes. Explainability is a core pillar of PolarisLex. For every evaluation, the platform generates a transparent reasoning path showing the exact legal requirement, the corresponding policy clause, supporting entities, and the evidence path used to reach the assessment.",
    },
    {
      q: "Does PolarisLex provide legal advice?",
      a: "No. PolarisLex is a compliance intelligence and research analysis tool. It is designed to assist privacy teams, compliance officers, and researchers by identifying coverage, gaps, and relationships. It does not provide legal advice and should not be used as a substitute for qualified legal counsel.",
    },
  ];

  return (
    <div className="pl-landing">
      {/* ── Sticky Header Navigation ── */}
      <header className="pl-nav-header">
        <div className="pl-container pl-nav-container">
          <a href="#" className="pl-brand-logo">
            <div className="pl-logo-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="5" r="3" fill="#2563EB" />
                <circle cx="5" cy="17" r="3" fill="#4F46E5" />
                <circle cx="19" cy="17" r="3" fill="#0284C7" />
                <line x1="12" y1="5" x2="5" y2="17" stroke="#2563EB" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="12" y1="5" x2="19" y2="17" stroke="#2563EB" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="5" y1="17" x2="19" y2="17" stroke="#4F46E5" strokeWidth="1.5" />
              </svg>
            </div>
            <span className="pl-brand-title">PolarisLex</span>
            <span className="pl-brand-badge">Compliance Graph</span>
          </a>

          <nav className="pl-nav-links">
            <a href="#product">Product</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#technology">Technology</a>
            <a href="#faq">FAQ</a>
          </nav>

          <div className="pl-nav-actions">
            <button className="pl-btn-secondary" onClick={onLogin}>Login</button>
            <button className="pl-btn-primary" onClick={onExplore}>
              Explore PolarisLex
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* ── HERO SECTION ── */}
      <section className="pl-hero-section">
        <div className="pl-container pl-hero-grid">
          <div className="pl-hero-content">
            <div className="pl-eyebrow-badge">
              <span className="pl-pulse-dot"></span>
              AI × Knowledge Graphs × Compliance
            </div>

            <h1 className="pl-hero-title">
              Turn Indian privacy requirements into an <span className="pl-text-gradient">explainable compliance map.</span>
            </h1>

            <p className="pl-hero-subtext">
              PolarisLex connects regulatory requirements, policy clauses, and compliance evidence through knowledge graphs and GraphRAG — helping teams understand what is covered, what is missing, and why.
            </p>

            <div className="pl-hero-cta-group">
              <button className="pl-btn-primary pl-btn-lg" onClick={onExplore}>
                Explore PolarisLex
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
              <a href="#how-it-works" className="pl-link-secondary">
                See how it works ↓
              </a>
            </div>

            <div className="pl-hero-trust-bar">
              <div className="pl-trust-item">
                <span className="pl-trust-bullet"></span>
                DPDP Act 2023 Ready
              </div>
              <div className="pl-trust-item">
                <span className="pl-trust-bullet"></span>
                GraphRAG Traversal
              </div>
              <div className="pl-trust-item">
                <span className="pl-trust-bullet"></span>
                Explainable Audit Trail
              </div>
            </div>
          </div>

          {/* Hero Right Visual: Connected Compliance Graph Diagram */}
          <div className="pl-hero-visual-card">
            <div className="pl-card-header">
              <div className="pl-card-dots">
                <span className="dot red"></span>
                <span className="dot yellow"></span>
                <span className="dot green"></span>
              </div>
              <span className="pl-card-title">Live Compliance Knowledge Path</span>
              <span className="pl-pill-live">Graph Active</span>
            </div>

            <div className="pl-hero-graph-canvas">
              <svg viewBox="0 0 540 360" className="pl-hero-svg">
                {/* Background Grid Pattern */}
                <defs>
                  <pattern id="hero-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                    <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(37,99,235,0.06)" strokeWidth="1" />
                  </pattern>
                  <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#4F46E5" stopOpacity="0.8" />
                  </linearGradient>
                </defs>

                <rect width="540" height="360" fill="url(#hero-grid)" />

                {/* Connecting Edges with Animated Pulsing Beams */}
                <g className="pl-svg-edges">
                  {/* Reg -> Req */}
                  <path d="M 90,180 L 190,100" stroke="url(#lineGrad)" strokeWidth="2.5" strokeDasharray="4 4" />
                  <path d="M 90,180 L 190,260" stroke="url(#lineGrad)" strokeWidth="2.5" strokeDasharray="4 4" />
                  
                  {/* Req -> Clause */}
                  <path d="M 190,100 L 310,130" stroke="url(#lineGrad)" strokeWidth="2.5" />
                  <path d="M 190,260 L 310,230" stroke="url(#lineGrad)" strokeWidth="2.5" />

                  {/* Clause -> Evidence */}
                  <path d="M 310,130 L 420,100" stroke="url(#lineGrad)" strokeWidth="2.5" />

                  {/* Clause -> Status */}
                  <path d="M 420,100 L 470,180" stroke="#10B981" strokeWidth="3" />
                  <path d="M 310,230 L 470,180" stroke="#F59E0B" strokeWidth="2.5" strokeDasharray="3 3" />
                </g>

                {/* Animated Particles flowing on lines */}
                <circle cx="140" cy="140" r="3.5" fill="#2563EB">
                  <animate attributeName="cx" values="90;190" dur="2.5s" repeatCount="indefinite" />
                  <animate attributeName="cy" values="180;100" dur="2.5s" repeatCount="indefinite" />
                </circle>
                <circle cx="250" cy="115" r="3.5" fill="#4F46E5">
                  <animate attributeName="cx" values="190;310" dur="2s" repeatCount="indefinite" />
                  <animate attributeName="cy" values="100;130" dur="2s" repeatCount="indefinite" />
                </circle>

                {/* Interactive Nodes */}
                {/* Node 1: Regulation */}
                <g 
                  className="pl-node-group" 
                  onMouseEnter={() => setHeroHoverNode("reg")}
                  onMouseLeave={() => setHeroHoverNode(null)}
                >
                  <circle cx="90" cy="180" r="28" fill="#EFF6FF" stroke="#2563EB" strokeWidth="2.5" />
                  <text x="90" y="176" textAnchor="middle" className="pl-svg-node-label">REGULATION</text>
                  <text x="90" y="190" textAnchor="middle" className="pl-svg-node-sub">DPDP Act</text>
                </g>

                {/* Node 2: Requirement */}
                <g 
                  className="pl-node-group" 
                  onMouseEnter={() => setHeroHoverNode("req")}
                  onMouseLeave={() => setHeroHoverNode(null)}
                >
                  <circle cx="190" cy="100" r="26" fill="#EEF2FF" stroke="#4F46E5" strokeWidth="2.5" />
                  <text x="190" y="96" textAnchor="middle" className="pl-svg-node-label">REQUIREMENT</text>
                  <text x="190" y="110" textAnchor="middle" className="pl-svg-node-sub">Consent Notice</text>
                </g>

                {/* Node 3: Policy Clause */}
                <g 
                  className="pl-node-group" 
                  onMouseEnter={() => setHeroHoverNode("clause")}
                  onMouseLeave={() => setHeroHoverNode(null)}
                >
                  <circle cx="310" cy="130" r="26" fill="#F0F9FF" stroke="#0284C7" strokeWidth="2.5" />
                  <text x="310" y="126" textAnchor="middle" className="pl-svg-node-label">POLICY CLAUSE</text>
                  <text x="310" y="140" textAnchor="middle" className="pl-svg-node-sub">Clause 4.1</text>
                </g>

                {/* Node 4: Evidence */}
                <g 
                  className="pl-node-group" 
                  onMouseEnter={() => setHeroHoverNode("evidence")}
                  onMouseLeave={() => setHeroHoverNode(null)}
                >
                  <circle cx="420" cy="100" r="26" fill="#ECFDF5" stroke="#059669" strokeWidth="2.5" />
                  <text x="420" y="96" textAnchor="middle" className="pl-svg-node-label">EVIDENCE</text>
                  <text x="420" y="110" textAnchor="middle" className="pl-svg-node-sub">UI Modal Log</text>
                </g>

                {/* Node 5: Status */}
                <g 
                  className="pl-node-group" 
                  onMouseEnter={() => setHeroHoverNode("status")}
                  onMouseLeave={() => setHeroHoverNode(null)}
                >
                  <circle cx="470" cy="180" r="30" fill="#ECFDF5" stroke="#10B981" strokeWidth="3" />
                  <text x="470" y="176" textAnchor="middle" className="pl-svg-node-label" fill="#047857">STATUS</text>
                  <text x="470" y="191" textAnchor="middle" className="pl-svg-node-sub" fill="#047857">Covered 96%</text>
                </g>
              </svg>

              {/* Node Inspector Tooltip Callout */}
              <div className="pl-graph-inspector-bar">
                {heroHoverNode ? (
                  <div className="pl-inspector-active">
                    <span className="pl-inspector-tag">{heroNodeInfo[heroHoverNode].title}</span>
                    <span className="pl-inspector-desc">{heroNodeInfo[heroHoverNode].detail}</span>
                  </div>
                ) : (
                  <div className="pl-inspector-placeholder">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    Hover over nodes to inspect relationship reasoning path
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 2 — THE PROBLEM ── */}
      <section className="pl-section pl-bg-alt" id="problem">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">Core Challenge</span>
            <h2 className="pl-section-title">
              Compliance isn't just about finding similar words.
            </h2>
            <p className="pl-section-subtitle">
              Indian legal & cybersecurity frameworks involve interconnected obligations, definitions, and exceptions. Text keyword matching leaves critical gaps.
            </p>
          </div>

          <div className="pl-comparison-grid">
            {/* Left Box: Traditional Document Review */}
            <div className="pl-comparison-card pl-card-flawed">
              <div className="pl-comp-header">
                <div className="pl-comp-badge badge-flawed">Traditional Approach</div>
                <h3>Keyword & Text Similarity Search</h3>
                <p>Scans raw PDFs for word occurrences without understanding legal hierarchy or relationships.</p>
              </div>

              <div className="pl-comp-flow">
                <div className="pl-flow-step">
                  <span className="step-num">1</span>
                  <span>PDF Document</span>
                </div>
                <div className="pl-flow-arrow">↓</div>
                <div className="pl-flow-step">
                  <span className="step-num">2</span>
                  <span>Keyword Query ("Consent")</span>
                </div>
                <div className="pl-flow-arrow">↓</div>
                <div className="pl-flow-step">
                  <span className="step-num">3</span>
                  <span>Isolated Text Snippets</span>
                </div>
                <div className="pl-flow-arrow">↓</div>
                <div className="pl-flow-step step-warning">
                  <span className="step-num">4</span>
                  <span>Manual Analysis & Guesswork</span>
                </div>
              </div>

              <ul className="pl-comp-checklist list-negative">
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  Misses statutory definitions & cross-references
                </li>
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  Treats every clause as an isolated text block
                </li>
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  No explainable audit trail for missing requirements
                </li>
              </ul>
            </div>

            {/* Right Box: PolarisLex Knowledge Graph */}
            <div className="pl-comparison-card pl-card-superior">
              <div className="pl-comp-header">
                <div className="pl-comp-badge badge-superior">PolarisLex Approach</div>
                <h3>Connected Knowledge Graph & GraphRAG</h3>
                <p>Models compliance as a connected graph of regulations, obligations, entities, clauses, and evidence.</p>
              </div>

              <div className="pl-comp-flow">
                <div className="pl-flow-step">
                  <span className="step-num">1</span>
                  <span>Regulatory Schema</span>
                </div>
                <div className="pl-flow-arrow">↓</div>
                <div className="pl-flow-step">
                  <span className="step-num">2</span>
                  <span>Knowledge Graph Construction</span>
                </div>
                <div className="pl-flow-arrow">↓</div>
                <div className="pl-flow-step">
                  <span className="step-num">3</span>
                  <span>GraphRAG Semantic Traversal</span>
                </div>
                <div className="pl-flow-arrow">↓</div>
                <div className="pl-flow-step step-success">
                  <span className="step-num">4</span>
                  <span>Explainable Compliance Map</span>
                </div>
              </div>

              <ul className="pl-comp-checklist list-positive">
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Maps explicit connections between statutory obligations
                </li>
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Identifies partial gaps & missing obligations instantly
                </li>
                <li>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Transparent reasoning path for every compliance status
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 3 — THE DIFFERENCE ── */}
      <section className="pl-section" id="difference">
        <div className="pl-container">
          <div className="pl-section-header">
            <span className="pl-section-kicker">Core Differentiator</span>
            <h2 className="pl-section-title">
              From documents to relationships.
            </h2>
            <p className="pl-section-subtitle">
              PolarisLex represents compliance as a connected system rather than a collection of isolated documents. Click any node below to inspect its connected regulatory graph.
            </p>
          </div>

          <div className="pl-interactive-kg-widget">
            <div className="pl-kg-canvas-container">
              <div className="pl-kg-node-grid">
                {Object.values(graphNodes).map((node) => {
                  const isSelected = selectedGraphNode === node.id;
                  const isConnected = graphNodes[selectedGraphNode]?.connections.includes(node.id);

                  return (
                    <div
                      key={node.id}
                      className={`pl-kg-node-card node-cat-${node.category.toLowerCase().replace(/\s+/g, '')} ${isSelected ? "is-selected" : ""} ${isConnected ? "is-connected" : ""}`}
                      onClick={() => setSelectedGraphNode(node.id)}
                    >
                      <div className="pl-kg-node-top">
                        <span className="pl-kg-category-tag">{node.category}</span>
                        {isSelected && <span className="pl-active-indicator">Selected Focus</span>}
                        {isConnected && <span className="pl-rel-indicator">Connected</span>}
                      </div>
                      <h4 className="pl-kg-node-title">{node.name}</h4>
                      <p className="pl-kg-node-desc">{node.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Node Details Sidecard */}
            <div className="pl-kg-detail-card">
              <div className="pl-kg-detail-header">
                <span className="pl-pill-blue">Node Inspector</span>
                <h3>{graphNodes[selectedGraphNode].name}</h3>
                <span className="pl-kg-type-badge">{graphNodes[selectedGraphNode].category}</span>
              </div>

              <p className="pl-kg-detail-text">{graphNodes[selectedGraphNode].desc}</p>

              <div className="pl-kg-connections-list">
                <h4>Direct Graph Connections ({graphNodes[selectedGraphNode].connections.length}):</h4>
                <div className="pl-kg-chip-group">
                  {graphNodes[selectedGraphNode].connections.map((targetId) => (
                    <button
                      key={targetId}
                      className="pl-kg-chip-btn"
                      onClick={() => setSelectedGraphNode(targetId)}
                    >
                      <span>→</span> {graphNodes[targetId]?.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pl-kg-formula-box">
                <span className="formula-title">Graph Triplet Relationship:</span>
                <code>({graphNodes[selectedGraphNode].name}) ──[MAPPED_OBLIGATION]──► (Policy Evidence)</code>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 4 — HOW IT WORKS ── */}
      <section className="pl-section pl-bg-alt" id="how-it-works">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">4-Step Workflow</span>
            <h2 className="pl-section-title">
              How PolarisLex analyzes your policy.
            </h2>
            <p className="pl-section-subtitle">
              A seamless, transparent pipeline that turns raw policy documents into connected legal intelligence.
            </p>
          </div>

          <div className="pl-workflow-grid">
            <div className="pl-workflow-card">
              <div className="pl-wf-number">01</div>
              <div className="pl-wf-icon-wrap">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563EB" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <h3>01 — Upload Document</h3>
              <p>Upload a privacy policy or compliance document in PDF, DOCX, HTML, or TXT format.</p>
              <div className="pl-wf-tags">
                <span>PDF</span> <span>DOCX</span> <span>HTML</span> <span>TXT</span>
              </div>
            </div>

            <div className="pl-workflow-card">
              <div className="pl-wf-number">02</div>
              <div className="pl-wf-icon-wrap">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <h3>02 — Understand & Extract</h3>
              <p>PolarisLex extracts clauses, entities, operational definitions, and compliance context.</p>
              <div className="pl-wf-tags">
                <span>NLP Parsing</span> <span>Entity Extraction</span>
              </div>
            </div>

            <div className="pl-workflow-card">
              <div className="pl-wf-number">03</div>
              <div className="pl-wf-icon-wrap">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0284C7" strokeWidth="2">
                  <circle cx="18" cy="5" r="3" />
                  <circle cx="6" cy="12" r="3" />
                  <circle cx="18" cy="19" r="3" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                </svg>
              </div>
              <h3>03 — Connect & GraphRAG</h3>
              <p>Connects extracted policy clauses with the regulatory knowledge graph and semantic evidence.</p>
              <div className="pl-wf-tags">
                <span>Knowledge Graph</span> <span>GraphRAG</span>
              </div>
            </div>

            <div className="pl-workflow-card">
              <div className="pl-wf-number">04</div>
              <div className="pl-wf-icon-wrap">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <h3>04 — Analyze & Explain</h3>
              <p>Receive an explainable compliance analysis showing Covered, Partial, and Missing statuses with proof.</p>
              <div className="pl-wf-tags">
                <span>Covered</span> <span>Partial</span> <span>Missing</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 5 — PRODUCT VISUAL ── */}
      <section className="pl-section" id="product">
        <div className="pl-container">
          <div className="pl-section-header">
            <span className="pl-section-kicker">Platform Interface</span>
            <h2 className="pl-section-title">
              Designed for clarity, precision, and auditability.
            </h2>
            <p className="pl-section-subtitle">
              Explore how PolarisLex presents compliance metrics, graph traversals, and clause evidence in a unified dashboard.
            </p>
          </div>

          {/* Product Dashboard Visual Mockup */}
          <div className="pl-dashboard-mockup">
            <div className="pl-db-topbar">
              <div className="pl-db-window-controls">
                <span className="pl-db-dot red"></span>
                <span className="pl-db-dot yellow"></span>
                <span className="pl-db-dot green"></span>
              </div>
              <div className="pl-db-address-bar">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                app.polarislex.ai/analysis/dpdp-compliance-2023
              </div>
              <div className="pl-db-actions">
                <span className="pl-db-badge">Sample Data</span>
              </div>
            </div>

            <div className="pl-db-nav-tabstrip">
              <button 
                className={`pl-db-tab ${activeTab === "overview" ? "is-active" : ""}`}
                onClick={() => setActiveTab("overview")}
              >
                Compliance Overview
              </button>
              <button 
                className={`pl-db-tab ${activeTab === "inspector" ? "is-active" : ""}`}
                onClick={() => setActiveTab("inspector")}
              >
                Clause Inspector
              </button>
              <button 
                className={`pl-db-tab ${activeTab === "reasoner" ? "is-active" : ""}`}
                onClick={() => setActiveTab("reasoner")}
              >
                Reasoning Path
              </button>
            </div>

            <div className="pl-db-body">
              {activeTab === "overview" && (
                <div className="pl-db-view-overview">
                  <div className="pl-db-metrics-row">
                    <div className="pl-metric-box">
                      <span className="metric-label">Overall Coverage Score</span>
                      <div className="metric-value-wrap">
                        <span className="metric-val">78.4%</span>
                        <span className="metric-tag tag-good">Good Coverage</span>
                      </div>
                      <div className="pl-progress-bar">
                        <div className="pl-progress-fill" style={{ width: "78.4%" }}></div>
                      </div>
                    </div>

                    <div className="pl-metric-box">
                      <span className="metric-label">Covered Obligations</span>
                      <div className="metric-value-wrap">
                        <span className="metric-val text-green">14</span>
                        <span className="metric-sub">/ 18 Requirements</span>
                      </div>
                    </div>

                    <div className="pl-metric-box">
                      <span className="metric-label">Partially Covered</span>
                      <div className="metric-value-wrap">
                        <span className="metric-val text-amber">3</span>
                        <span className="metric-sub">Ambiguous clauses</span>
                      </div>
                    </div>

                    <div className="pl-metric-box">
                      <span className="metric-label">Missing Obligations</span>
                      <div className="metric-value-wrap">
                        <span className="metric-val text-red">1</span>
                        <span className="metric-sub">Gap detected</span>
                      </div>
                    </div>
                  </div>

                  <div className="pl-db-split-panel">
                    <div className="pl-db-left-panel">
                      <h4>Regulatory Requirements Status (DPDP Act 2023)</h4>
                      <div className="pl-req-list">
                        <div className="pl-req-item status-covered">
                          <span className="status-badge badge-covered">COVERED</span>
                          <div className="req-info">
                            <h5>Sec 6(1) — Explicit Consent Notice</h5>
                            <p>Mapped to Policy Clause 4.1 with 96% semantic match</p>
                          </div>
                        </div>
                        <div className="pl-req-item status-covered">
                          <span className="status-badge badge-covered">COVERED</span>
                          <div className="req-info">
                            <h5>Sec 8(5) — Reasonable Security Safeguards</h5>
                            <p>Mapped to Policy Clause 8.3 & SOC2 evidence</p>
                          </div>
                        </div>
                        <div className="pl-req-item status-partial">
                          <span className="status-badge badge-partial">PARTIAL</span>
                          <div className="req-info">
                            <h5>Sec 12 — Right to Grievance Redressal</h5>
                            <p>Clause mentions contact email but omits DPO officer details</p>
                          </div>
                        </div>
                        <div className="pl-req-item status-missing">
                          <span className="status-badge badge-missing">MISSING</span>
                          <div className="req-info">
                            <h5>Sec 9 — Data Erasure & Retention Limits</h5>
                            <p>No clause identified governing data erasure upon consent revocation</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="pl-db-right-panel">
                      <div className="pl-graph-preview-box">
                        <div className="pl-graph-box-header">
                          <span>Graph Sub-Tree View</span>
                          <span className="pl-code-small">Sec 6(1) Consent Graph</span>
                        </div>
                        <div className="pl-graph-mini-visual">
                          <div className="mini-node reg-node">DPDP Act Sec 6</div>
                          <div className="mini-line"></div>
                          <div className="mini-node req-node">Consent Obligation</div>
                          <div className="mini-line"></div>
                          <div className="mini-node clause-node">Clause 4.1 (Opt-in)</div>
                        </div>
                        <div className="pl-graph-mini-desc">
                          <strong>Graph Traversal:</strong> Traversed 3 hops from Statutory Mandate to Policy Clause 4.1. Evidence confidence score: 0.94.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "inspector" && (
                <div className="pl-db-view-inspector">
                  <div className="pl-inspector-split">
                    <div className="pl-inspector-left">
                      <span className="panel-kicker">Target Policy Extract</span>
                      <h4>Uploaded Privacy Policy — Section 4</h4>
                      <div className="pl-policy-snippet">
                        <p className="highlight-clause">
                          <span className="clause-tag">Clause 4.1</span> "We process personal data only after obtaining clear, explicit consent from the user via our interactive opt-in modal. Users retain the right to withdraw consent at any given time by visiting Account Preferences."
                        </p>
                        <p>
                          "Clause 4.2 Data retention details: Data is stored for operational requirements until explicit deletion requests are submitted by the data principal."
                        </p>
                      </div>
                    </div>
                    <div className="pl-inspector-right">
                      <span className="panel-kicker">Matched Regulatory Requirement</span>
                      <h4>DPDP Act 2023 — Section 6: Notice & Consent</h4>
                      <div className="pl-matched-box">
                        <div className="pl-match-header">
                          <span className="badge-covered">EXACT MATCH (96%)</span>
                          <span className="time-tag">Mapped via GraphRAG</span>
                        </div>
                        <p className="match-text">
                          <strong>Statutory Text:</strong> "The Data Fiduciary shall give to the Data Principal an itemized notice stating the personal data sought to be processed and the purpose of processing..."
                        </p>
                        <div className="match-analysis">
                          <strong>Graph Relationship:</strong> Clause 4.1 explicitly satisfies Notice, Purpose Specification, and Consent Revocation sub-requirements.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "reasoner" && (
                <div className="pl-db-view-reasoner">
                  <span className="panel-kicker">Explainable Audit Trail</span>
                  <h4>Reasoning Chain for Grievance Redressal (Sec 12)</h4>

                  <div className="pl-reasoning-timeline">
                    <div className="pl-rt-step">
                      <div className="rt-node">1</div>
                      <div className="rt-content">
                        <h5>Regulatory Mandate Identification</h5>
                        <p>DPDP Act 2023 Sec 12 requires Data Fiduciary to publish contact details of a Data Protection Officer or Grievance Officer.</p>
                      </div>
                    </div>
                    <div className="pl-rt-step">
                      <div className="rt-node">2</div>
                      <div className="rt-content">
                        <h5>Semantic & Graph Search</h5>
                        <p>Traversed policy graph for entities: [Grievance Officer, DPO, Redressal Email, Escalation Contact].</p>
                      </div>
                    </div>
                    <div className="pl-rt-step">
                      <div className="rt-node">3</div>
                      <div className="rt-content">
                        <h5>Clause Mapping & Gap Detection</h5>
                        <p>Policy Clause 11 contains generic support email (`support@company.com`) but lacks designated Grievance Officer name & statutory contact address.</p>
                      </div>
                    </div>
                    <div className="pl-rt-step rt-step-warning">
                      <div className="rt-node">4</div>
                      <div className="rt-content">
                        <h5>Status Assessment: PARTIAL COVERAGE</h5>
                        <p>Assessment score: 55%. Grievance mechanism exists, but statutory DPO publishing mandate is incomplete.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 6 — COMPLIANCE INTELLIGENCE ── */}
      <section className="pl-section pl-bg-alt" id="intelligence">
        <div className="pl-container">
          <div className="pl-section-header">
            <span className="pl-section-kicker">Coverage Categorization</span>
            <h2 className="pl-section-title">
              See what's covered. Understand what's missing.
            </h2>
            <p className="pl-section-subtitle">
              PolarisLex classifies every regulatory requirement into three distinct compliance states with attached relationship evidence.
            </p>
          </div>

          <div className="pl-cards-grid-3">
            {/* Card 1: Covered */}
            <div className="pl-card-status border-covered">
              <div className="pl-status-badge badge-covered">
                <span className="status-dot green"></span>
                COVERED
              </div>
              <h3>Covered Requirements</h3>
              <p>Requirements supported by explicit, verifiable policy clauses and corresponding operational evidence.</p>

              <div className="pl-status-example">
                <div className="example-header">
                  <span>DPDP Act Sec 6 — Consent Notice</span>
                  <span className="score text-green">100% Mapped</span>
                </div>
                <div className="example-snippet">
                  "Clause 4.1 explicitly outlines itemized consent notice and opt-out options."
                </div>
              </div>
            </div>

            {/* Card 2: Partial */}
            <div className="pl-card-status border-partial">
              <div className="pl-status-badge badge-partial">
                <span className="status-dot amber"></span>
                PARTIAL
              </div>
              <h3>Partially Covered</h3>
              <p>Requirements with incomplete, ambiguous, or outdated policy clauses requiring clarification.</p>

              <div className="pl-status-example">
                <div className="example-header">
                  <span>CERT-In — Incident Reporting</span>
                  <span className="score text-amber">55% Mapped</span>
                </div>
                <div className="example-snippet">
                  "Policy mentions security logging, but omits mandatory 6-hour CERT-In notification window."
                </div>
              </div>
            </div>

            {/* Card 3: Missing */}
            <div className="pl-card-status border-missing">
              <div className="pl-status-badge badge-missing">
                <span className="status-dot red"></span>
                MISSING
              </div>
              <h3>Missing Requirements</h3>
              <p>Mandatory regulatory requirements for which no corresponding policy clause or evidence could be identified.</p>

              <div className="pl-status-example">
                <div className="example-header">
                  <span>DPDP Act Sec 9 — Erasure Limit</span>
                  <span className="score text-red">0% Mapped</span>
                </div>
                <div className="example-snippet">
                  "No policy clause found governing automatic data deletion upon consent revocation."
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 7 — EXPLAINABILITY ── */}
      <section className="pl-section" id="explainability">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">Transparent Analysis</span>
            <h2 className="pl-section-title">
              Don't just get an answer. See why.
            </h2>
            <p className="pl-section-subtitle">
              Trace the exact connection from regulatory requirement to policy evidence through our 5-stage explainable reasoning path.
            </p>
          </div>

          <div className="pl-reasoning-path-widget">
            <div className="pl-path-flow">
              <div 
                className={`pl-path-node ${reasonStep === 0 ? "is-active" : ""}`}
                onClick={() => setReasonStep(0)}
              >
                <span className="node-step">01</span>
                <span className="node-title">Regulatory Requirement</span>
              </div>
              <div className="pl-path-connector">→</div>

              <div 
                className={`pl-path-node ${reasonStep === 1 ? "is-active" : ""}`}
                onClick={() => setReasonStep(1)}
              >
                <span className="node-step">02</span>
                <span className="node-title">Policy Clause</span>
              </div>
              <div className="pl-path-connector">→</div>

              <div 
                className={`pl-path-node ${reasonStep === 2 ? "is-active" : ""}`}
                onClick={() => setReasonStep(2)}
              >
                <span className="node-step">03</span>
                <span className="node-title">Supporting Entity</span>
              </div>
              <div className="pl-path-connector">→</div>

              <div 
                className={`pl-path-node ${reasonStep === 3 ? "is-active" : ""}`}
                onClick={() => setReasonStep(3)}
              >
                <span className="node-step">04</span>
                <span className="node-title">Assessment</span>
              </div>
              <div className="pl-path-connector">→</div>

              <div 
                className={`pl-path-node ${reasonStep === 4 ? "is-active" : ""}`}
                onClick={() => setReasonStep(4)}
              >
                <span className="node-step">05</span>
                <span className="node-title">Evidence & Proof</span>
              </div>
            </div>

            <div className="pl-path-card-display">
              {reasonStep === 0 && (
                <div className="pl-path-content">
                  <span className="step-tag">STAGE 01 — REGULATORY REQUIREMENT</span>
                  <h3>DPDP Act 2023 Section 8(5)</h3>
                  <p>"A Data Fiduciary shall protect personal data in its possession or under its control by taking reasonable security safeguards to prevent data breach."</p>
                  <div className="meta-info">Key Entities: [Data Fiduciary, Personal Data, Security Safeguards, Breach Prevention]</div>
                </div>
              )}

              {reasonStep === 1 && (
                <div className="pl-path-content">
                  <span className="step-tag">STAGE 02 — RELEVANT POLICY CLAUSE</span>
                  <h3>Privacy Policy — Clause 8.3</h3>
                  <p>"We implement organizational and technical security measures, including AES-256 encryption at rest and TLS 1.3 in transit, to protect collected user information."</p>
                  <div className="meta-info">Matched via Vector & Subgraph Embedding (Cosine Similarity: 0.89)</div>
                </div>
              )}

              {reasonStep === 2 && (
                <div className="pl-path-content">
                  <span className="step-tag">STAGE 03 — SUPPORTING ENTITY / CONCEPT</span>
                  <h3>Connected Graph Entities</h3>
                  <p>Knowledge graph traversed related entities: <code>[Technical Safeguards]</code> ──► <code>[Encryption Standard]</code> ──► <code>[Access Controls]</code>.</p>
                  <div className="meta-info">Knowledge Graph Node ID: #entity-security-safeguard-08</div>
                </div>
              )}

              {reasonStep === 3 && (
                <div className="pl-path-content">
                  <span className="step-tag">STAGE 04 — COMPLIANCE ASSESSMENT</span>
                  <h3>Status: COVERED (Confidence 94%)</h3>
                  <p>Clause 8.3 explicitly satisfies the statutory requirement for technical security safeguards under DPDP Act Sec 8(5).</p>
                  <div className="meta-info">Assessment Generated via Deterministic Graph Logic + GraphRAG</div>
                </div>
              )}

              {reasonStep === 4 && (
                <div className="pl-path-content">
                  <span className="step-tag">STAGE 05 — EVIDENCE & EXPLANATION</span>
                  <h3>Verifiable Audit Citation</h3>
                  <p>Reference: Policy Doc Line 142-148, matched with SOC2 Type II Certification Artifact ID #SOC2-2024-SEC.</p>
                  <div className="meta-info">Traceable directly to source document coordinates</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 8 — TECHNOLOGY ── */}
      <section className="pl-section pl-bg-alt" id="technology">
        <div className="pl-container">
          <div className="pl-section-header">
            <span className="pl-section-kicker">Architecture & Engineering</span>
            <h2 className="pl-section-title">
              Built on connected intelligence.
            </h2>
            <p className="pl-section-subtitle">
              PolarisLex integrates knowledge graphs, GraphRAG, and hybrid retrieval into a robust compliance processing pipeline.
            </p>
          </div>

          {/* Architecture Pipeline Visual */}
          <div className="pl-arch-pipeline-card">
            <div className="arch-pipeline-title">System Execution Pipeline</div>
            <div className="pl-arch-nodes">
              <div className="arch-node">
                <span className="arch-step">1</span>
                <span>Document Input</span>
              </div>
              <div className="arch-arrow">→</div>
              <div className="arch-node">
                <span className="arch-step">2</span>
                <span>Clause & Entity Extraction</span>
              </div>
              <div className="arch-arrow">→</div>
              <div className="arch-node">
                <span className="arch-step">3</span>
                <span>Graph Representation</span>
              </div>
              <div className="arch-arrow">→</div>
              <div className="arch-node arch-node-highlight">
                <span className="arch-step">4</span>
                <span>Knowledge Graph & GraphRAG</span>
              </div>
              <div className="arch-arrow">→</div>
              <div className="arch-node">
                <span className="arch-step">5</span>
                <span>Hybrid Retrieval</span>
              </div>
              <div className="arch-arrow">→</div>
              <div className="arch-node">
                <span className="arch-step">6</span>
                <span>Explainable Report</span>
              </div>
            </div>
          </div>

          <div className="pl-tech-cards-grid">
            <div className="pl-tech-card">
              <div className="tech-icon-wrap">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563EB" strokeWidth="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
              </div>
              <h3>Knowledge Graphs</h3>
              <p>Represent regulatory mandates, obligations, entities, and definitions as a structured, queryable knowledge schema.</p>
            </div>

            <div className="pl-tech-card">
              <div className="tech-icon-wrap">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
              </div>
              <h3>GraphRAG</h3>
              <p>Retrieves contextual information along graph traversal paths rather than isolated vector distance chunks.</p>
            </div>

            <div className="pl-tech-card">
              <div className="tech-icon-wrap">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284C7" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </div>
              <h3>Semantic Search</h3>
              <p>Finds relevant policy evidence based on conceptual intent even when different legal terminology is used.</p>
            </div>

            <div className="pl-tech-card">
              <div className="tech-icon-wrap">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              </div>
              <h3>Graph Traversal</h3>
              <p>Explores multi-hop connections between legal mandates, operational definitions, and policy clauses.</p>
            </div>

            <div className="pl-tech-card">
              <div className="tech-icon-wrap">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D97706" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
              </div>
              <h3>Hybrid Retrieval</h3>
              <p>Combines graph structure with dense vector embeddings to achieve high precision and recall.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 9 — KNOWLEDGE SOURCES ── */}
      <section className="pl-section" id="sources">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">Regulatory Ecosystem</span>
            <h2 className="pl-section-title">
              Supported Indian Regulatory Frameworks.
            </h2>
            <p className="pl-section-subtitle">
              PolarisLex integrates key Indian privacy, data protection, and cybersecurity laws into a unified compliance graph.
            </p>
          </div>

          <div className="pl-sources-grid">
            <div className="pl-source-card">
              <div className="source-badge">ACT 2023</div>
              <h3>DPDP Act</h3>
              <span className="source-full">Digital Personal Data Protection Act, 2023</span>
              <p>Focuses on Data Fiduciary obligations, consent notices, data principal rights, DPO requirements, and cross-border transfer rules.</p>
            </div>

            <div className="pl-source-card">
              <div className="source-badge">ACT 2000</div>
              <h3>IT Act</h3>
              <span className="source-full">Information Technology Act, 2000</span>
              <p>Governs electronic records, digital signatures, cybersecurity compliance, and legal frameworks for cyber offences.</p>
            </div>

            <div className="pl-source-card">
              <div className="source-badge">RULES 2011</div>
              <h3>SPDI Rules</h3>
              <span className="source-full">Sensitive Personal Data Rules, 2011</span>
              <p>Specifies rules for collecting, receiving, storing, and handling sensitive personal data or information (SPDI).</p>
            </div>

            <div className="pl-source-card">
              <div className="source-badge">DIRECTIONS 2022</div>
              <h3>CERT-In Directions</h3>
              <span className="source-full">Cybersecurity Directions, 2022</span>
              <p>Mandates 6-hour cyber incident reporting, log retention standards, and system security synchronizations.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 10 — BEFORE / AFTER ── */}
      <section className="pl-section pl-bg-alt" id="before-after">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">Transformation</span>
            <h2 className="pl-section-title">
              A modern upgrade to compliance analysis.
            </h2>
          </div>

          <div className="pl-ba-table">
            <div className="ba-header-row">
              <div className="ba-col col-feature">Analysis Dimension</div>
              <div className="ba-col col-before">Traditional Manual Review</div>
              <div className="ba-col col-after">With PolarisLex</div>
            </div>

            <div className="ba-row">
              <div className="ba-col col-feature">Document Representation</div>
              <div className="ba-col col-before">Isolated PDFs & Text Snippets</div>
              <div className="ba-col col-after">Connected Knowledge Graph</div>
            </div>

            <div className="ba-row">
              <div className="ba-col col-feature">Regulatory Retrieval</div>
              <div className="ba-col col-before">Exact Keyword Search</div>
              <div className="ba-col col-after">GraphRAG Semantic Traversal</div>
            </div>

            <div className="ba-row">
              <div className="ba-col col-feature">Gap Identification</div>
              <div className="ba-col col-before">Manual Checklist Comparison</div>
              <div className="ba-col col-after">Automated Multi-hop Mapping</div>
            </div>

            <div className="ba-row">
              <div className="ba-col col-feature">Explainability</div>
              <div className="ba-col col-before">Subjective Auditor Notes</div>
              <div className="ba-col col-after">Verifiable Reasoning Audit Trail</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 11 — WHO IT IS FOR ── */}
      <section className="pl-section" id="audience">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">Target Audience</span>
            <h2 className="pl-section-title">
              Engineered for multidisciplinary teams.
            </h2>
          </div>

          <div className="pl-audience-grid">
            <div className="pl-aud-card">
              <div className="aud-icon">⚖️</div>
              <h3>Compliance Teams</h3>
              <p>Understand policy coverage and identify potential gaps across complex Indian mandates quickly.</p>
            </div>

            <div className="pl-aud-card">
              <div className="aud-icon">🛡️</div>
              <h3>Security Teams</h3>
              <p>Connect technical security policy requirements with CERT-In and IT Act obligations.</p>
            </div>

            <div className="pl-aud-card">
              <div className="aud-icon">🔒</div>
              <h3>Privacy Professionals</h3>
              <p>Trace DPDP Act obligations directly to policy clauses and operational evidence.</p>
            </div>

            <div className="pl-aud-card">
              <div className="aud-icon">🎓</div>
              <h3>Researchers</h3>
              <p>Explore the intersection of knowledge graphs, GraphRAG, and legal technology.</p>
            </div>

            <div className="pl-aud-card">
              <div className="aud-icon">📜</div>
              <h3>Policy Makers</h3>
              <p>Understand regulatory requirements through connected representations and schema mappings.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 12 — RESEARCH CREDIBILITY ── */}
      <section className="pl-section pl-bg-alt" id="research">
        <div className="pl-container">
          <div className="pl-research-card">
            <div className="pl-research-header">
              <span className="pl-eyebrow-badge">University Research & Engineering</span>
              <h2>Grounding AI in structured legal knowledge.</h2>
              <p>
                PolarisLex is a technology research project exploring how <strong>Knowledge Graphs + GraphRAG + Hybrid Retrieval</strong> can transform complex regulatory analysis into explainable, deterministic intelligence layer.
              </p>
            </div>

            <div className="pl-research-pipeline-box">
              <span className="pipeline-label">Academic GraphIR Pipeline Architecture:</span>
              <div className="pipeline-flow-str">
                <code>Document</code> ➔ <code>GraphIR Extract</code> ➔ <code>Knowledge Graph</code> ➔ <code>GraphRAG Retrieval</code> ➔ <code>Compliance Map</code>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 13 — FAQ ── */}
      <section className="pl-section" id="faq">
        <div className="pl-container">
          <div className="pl-section-header text-center">
            <span className="pl-section-kicker">Frequently Asked Questions</span>
            <h2 className="pl-section-title">
              Clear answers about PolarisLex.
            </h2>
          </div>

          <div className="pl-faq-accordion">
            {faqList.map((faq, index) => {
              const isOpen = activeFaq === index;
              return (
                <div key={index} className={`pl-faq-item ${isOpen ? "is-open" : ""}`}>
                  <button className="pl-faq-question" onClick={() => toggleFaq(index)}>
                    <span>{faq.q}</span>
                    <span className="faq-icon">{isOpen ? "−" : "+"}</span>
                  </button>
                  {isOpen && (
                    <div className="pl-faq-answer">
                      <p>{faq.a}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA SECTION ── */}
      <section className="pl-final-cta-section">
        <div className="pl-container text-center">
          <h2 className="pl-final-cta-title">
            Make compliance easier to understand.
          </h2>
          <p className="pl-final-cta-subtext">
            Explore how PolarisLex connects regulations, policies, and evidence into an explainable compliance intelligence layer.
          </p>

          <div className="pl-cta-center-wrap">
            <button className="pl-btn-primary pl-btn-xl" onClick={onExplore}>
              Explore PolarisLex
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="pl-footer">
        <div className="pl-container pl-footer-grid">
          <div className="pl-footer-brand">
            <div className="pl-brand-logo">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="5" r="3" fill="#2563EB" />
                <circle cx="5" cy="17" r="3" fill="#4F46E5" />
                <circle cx="19" cy="17" r="3" fill="#0284C7" />
                <line x1="12" y1="5" x2="5" y2="17" stroke="#2563EB" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="12" y1="5" x2="19" y2="17" stroke="#2563EB" strokeWidth="2" strokeDasharray="3 3" />
              </svg>
              <span className="pl-brand-title">PolarisLex</span>
            </div>
            <p className="pl-footer-desc">
              Knowledge Graph Powered Indian Legal Compliance Intelligence Platform.
            </p>
          </div>

          <div className="pl-footer-links">
            <h4>Platform</h4>
            <a href="#product">Product Visuals</a>
            <a href="#how-it-works">4-Step Workflow</a>
            <a href="#technology">Technology & GraphRAG</a>
            <a href="#sources">Supported Regulations</a>
          </div>

          <div className="pl-footer-links">
            <h4>Explore</h4>
            <button className="pl-footer-btn-link" onClick={onExplore}>
              Interactive Platform Demo
            </button>
            <a href="#faq">FAQ</a>
            <a href="#research">Research Credibility</a>
          </div>

          <div className="pl-footer-legal">
            <h4>Legal & Research Disclaimer</h4>
            <p>
              PolarisLex is a compliance intelligence research project. It does not provide definitive legal advice or replace qualified legal professionals.
            </p>
          </div>
        </div>

        <div className="pl-container pl-footer-bottom">
          <span>&copy; {new Date().getFullYear()} PolarisLex Project. All rights reserved.</span>
          <span>Designed with precision for compliance & legal AI research.</span>
        </div>
      </footer>
    </div>
  );
}
