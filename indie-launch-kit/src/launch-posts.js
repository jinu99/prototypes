/**
 * Generate launch post drafts for Product Hunt, Reddit, and Hacker News.
 */
export function generateLaunchPosts(meta, sections) {
  const name = meta.name || 'My Project';
  const desc = meta.description || sections.hero?.title || 'An awesome project';
  const heroDesc = stripHtml(sections.hero?.description || '').trim();
  const shortDesc = heroDesc.split('\n').filter(Boolean)[0] || desc;

  const featureList = [];
  for (const f of (sections.features || [])) {
    for (const item of (f.items || [])) {
      featureList.push(stripHtml(item).trim());
    }
  }
  const featuresText = featureList.length
    ? featureList.slice(0, 5).map(f => `- ${f}`).join('\n')
    : '- Check out the README for full feature list';

  const installText = sections.install?.[0]?.codeBlocks?.[0]?.code || `npm install ${name}`;

  return {
    productHunt: generateProductHunt(name, desc, shortDesc, featuresText),
    reddit: generateReddit(name, desc, shortDesc, featuresText, installText),
    hackerNews: generateHackerNews(name, desc, shortDesc),
  };
}

function generateProductHunt(name, tagline, desc, features) {
  return `# Product Hunt Launch Post

**Product Name:** ${name}

**Tagline:** ${tagline}

**Description:**
${desc}

**Key Features:**
${features}

---

**Maker Comment (first comment):**

Hey everyone! 👋

I'm excited to share ${name} with you today.

${desc}

I built this because I wanted a simpler way to solve this problem. Would love to hear your feedback and suggestions!

What would you like to see next? Drop a comment below! 🚀
`;
}

function generateReddit(name, tagline, desc, features, install) {
  return `# Reddit Launch Post

**Suggested subreddits:** r/opensource, r/programming, r/webdev, r/SideProject

**Title:** I built ${name} — ${tagline}

**Body:**

Hey r/[subreddit]!

I've been working on **${name}** and just released it. ${desc}

## What it does

${features}

## Quick Start

\`\`\`
${install}
\`\`\`

## Links

- GitHub: [link]
- Demo: [link]

Would love to hear your thoughts! Happy to answer any questions.
`;
}

function generateHackerNews(name, tagline, desc) {
  return `# Hacker News Launch Post

**Title:** Show HN: ${name} – ${tagline}

**URL:** [project URL]

**Text (if no URL):**

${desc}

I built ${name} because ${tagline.toLowerCase()}.

Key design decisions:
- [Add 2-3 interesting technical decisions]

Looking forward to feedback from the HN community.
`;
}

function stripHtml(html) {
  return html.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"');
}
