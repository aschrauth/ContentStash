/**
 * Simple test script for YouTube extractor
 * Run this in a browser console on a YouTube video page to test extraction
 */

// Test video ID extraction
const testUrls = [
  'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
  'https://youtu.be/dQw4w9WgXcQ',
  'https://www.youtube.com/embed/dQw4w9WgXcQ',
];

console.log('Testing URL parsing:');
testUrls.forEach(url => {
  const videoId = extractVideoId(url);
  console.log(`${url} -> ${videoId}`);
});

// Test YouTube URL detection
console.log('\nTesting YouTube URL detection:');
console.log('youtube.com URL:', isYouTubeUrl('https://www.youtube.com/watch?v=test'));
console.log('youtu.be URL:', isYouTubeUrl('https://youtu.be/test'));
console.log('Non-YouTube URL:', isYouTubeUrl('https://example.com'));

// Test transcript extraction (requires being on a YouTube page)
console.log('\nTesting transcript extraction...');
console.log('Note: This must be run on a YouTube video page with captions');

// Helper functions (copy from youtube-extractor.ts)
function extractVideoId(url) {
  try {
    const urlObj = new URL(url);
    
    if (urlObj.hostname.includes('youtube.com') && urlObj.pathname === '/watch') {
      return urlObj.searchParams.get('v');
    }
    
    if (urlObj.hostname === 'youtu.be') {
      return urlObj.pathname.slice(1);
    }
    
    if (urlObj.hostname.includes('youtube.com') && urlObj.pathname.startsWith('/embed/')) {
      return urlObj.pathname.split('/')[2];
    }
    
    return null;
  } catch (error) {
    console.error('Error parsing URL:', error);
    return null;
  }
}

function isYouTubeUrl(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.includes('youtube.com') || urlObj.hostname === 'youtu.be';
  } catch {
    return false;
  }
}

console.log('\n✓ Basic tests completed');
console.log('To test full extraction, use: extractYouTubeTranscript("VIDEO_ID")');