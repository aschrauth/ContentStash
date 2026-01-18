"use client";

import { SavedItem } from './store';

// --- Simulation Utilities ---

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export async function simulateMetadataFetch(url: string): Promise<{
  title: string;
  description: string;
  imageUrl: string;
  faviconUrl: string;
  suggestedTags: string[];
  suggestedTopic: string;
}> {
  await delay(1500); // 1.5s delay

  // Mock data based on URL keywords or random
  const isDesign = url.includes('design') || url.includes('ui') || url.includes('ux');
  
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    return {
      title: "Understanding the Future of AI in Product Design",
      description: "In this video, we explore how artificial intelligence is reshaping the landscape of product design and what it means for the future of UX.",
      imageUrl: "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80",
      faviconUrl: "https://www.youtube.com/s/desktop/12d6b690/img/favicon.ico",
      suggestedTags: ['ai', 'product-design', 'ux', 'future-tech'],
      suggestedTopic: 'Design',
    };
  }

  if (isDesign) {
    return {
      title: "10 Principles of Good Design - A Modern Take",
      description: "Dieter Rams' principles are timeless, but how do they apply to the modern web? We break down each principle with contemporary examples.",
      imageUrl: "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&q=80",
      faviconUrl: "https://framer.com/images/favicon.png", // Generic favicon
      suggestedTags: ['design-principles', 'web-design', 'dieter-rams', 'inspiration'],
      suggestedTopic: 'Design',
    };
  }

  return {
    title: "The State of Frontend Development in 2024",
    description: "A comprehensive look at the tools, frameworks, and methodologies defining the frontend landscape this year.",
    imageUrl: "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&q=80",
    faviconUrl: "https://github.githubassets.com/favicons/favicon.svg",
    suggestedTags: ['frontend', 'web-dev', 'javascript', 'trends-2024'],
    suggestedTopic: 'Engineering',
  };
}

export async function simulateContentExtraction(url: string): Promise<{
  archivedText: string;
  suggestedTags: string[];
  suggestedTopic: string;
}> {
  await delay(2500); // 2.5s delay

  // Random failure chance (10%)
  if (Math.random() < 0.1) {
    throw new Error("Failed to extract content");
  }

  const isDesign = url.includes('design') || url.includes('ui');

  if (isDesign) {
    return {
      archivedText: `Good design is innovative. The possibilities for innovation are not, by any means, exhausted. Technological development is always offering new opportunities for innovative design. But innovative design always develops in tandem with innovative technology, and can never be an end in itself. Good design makes a product useful. A product is bought to be used. It has to satisfy certain criteria, not only functional, but also psychological and aesthetic. Good design emphasizes the usefulness of a product whilst disregarding anything that could possibly detract from it.`,
      suggestedTags: ['design-principles', 'innovation', 'ux', 'product-design'],
      suggestedTopic: 'Design',
    };
  }

  return {
    archivedText: `Frontend development has seen a massive shift towards server-side rendering and static site generation. Frameworks like Next.js and Remix are leading the charge, offering developers better performance and SEO out of the box. However, the complexity of the build chain has also increased. We are seeing a return to simplicity with tools that aim to reduce configuration overhead.`,
    suggestedTags: ['frontend', 'web-dev', 'react', 'performance'],
    suggestedTopic: 'Engineering',
  };
}

export async function simulateContentAnalysis(text: string): Promise<{
  title: string;
  description: string;
  tags: string[];
}> {
  await delay(2000); // 2s delay

  // Simple heuristic analysis
  const words = text.split(/\s+/);
  const title = words.slice(0, 8).join(' ') + (words.length > 8 ? '...' : '');
  const description = text.slice(0, 150) + (text.length > 150 ? '...' : '');
  
  // Mock tags based on content keywords
  const tags = [];
  const lowerText = text.toLowerCase();
  if (lowerText.includes('react') || lowerText.includes('javascript')) tags.push('development');
  if (lowerText.includes('design') || lowerText.includes('ui')) tags.push('design');
  if (lowerText.includes('ai') || lowerText.includes('llm')) tags.push('ai');
  if (lowerText.includes('product')) tags.push('product');
  if (tags.length === 0) tags.push('general');

  return {
    title: title.replace(/[#*]/g, '').trim(), // Remove markdown chars from title
    description: description.replace(/[#*]/g, '').trim(),
    tags
  };
}

export async function simulateRAGChat(
  question: string, 
  library: SavedItem[]
): Promise<{
  answer: string;
  citations: { savedItemId: string; excerpt: string; title: string }[];
}> {
  await delay(2000); // 2s delay

  // Simple keyword matching simulation
  const keywords = question.toLowerCase().split(' ').filter(w => w.length > 3);
  
  const relevantItems = library.filter(item => {
    const text = (item.title + ' ' + (item.archivedText || '') + ' ' + (item.notesMarkdown || '')).toLowerCase();
    return keywords.some(k => text.includes(k));
  }).slice(0, 3);

  if (relevantItems.length === 0) {
    return {
      answer: "I couldn't find any specific information in your library matching that question. Try saving more content related to this topic or refining your search terms.",
      citations: []
    };
  }

  const citations = relevantItems.map(item => ({
    savedItemId: item.id,
    title: item.title,
    excerpt: item.archivedText 
      ? item.archivedText.substring(0, 150) + "..." 
      : (item.description || "No content available").substring(0, 150) + "..."
  }));

  return {
    answer: `Based on your saved content, here is what I found regarding "${question}". \n\nSeveral sources in your library touch on this. The content suggests that ${keywords[0] || 'this topic'} is a key area of focus. Specifically, your saved items mention the importance of context and modern methodologies. \n\nRefer to the citations below for more details.`,
    citations
  };
}

