'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, Sparkles, Shield, TrendingUp, Zap, CreditCard, ArrowRight } from 'lucide-react';
import { StoryItem } from '@/lib/neobank/types';

interface StoryViewerModalProps {
  story: StoryItem | null;
  allStories: StoryItem[];
  isOpen: boolean;
  onClose: () => void;
  onSelectStory: (story: StoryItem) => void;
  onActionClick?: (actionType: string) => void;
}

export default function StoryViewerModal({
  story,
  allStories,
  isOpen,
  onClose,
  onSelectStory,
  onActionClick,
}: StoryViewerModalProps) {
  const [progress, setProgress] = useState(0);

  const currentIndex = story ? allStories.findIndex((s) => s.id === story.id) : 0;

  useEffect(() => {
    if (!isOpen || !story) return;

    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          // Advance to next story if available
          if (currentIndex < allStories.length - 1) {
            onSelectStory(allStories[currentIndex + 1]);
            return 0;
          } else {
            onClose();
            return 100;
          }
        }
        return prev + 2; // 50 ticks * 100ms = 5000ms (5 seconds)
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isOpen, story, currentIndex, allStories, onClose, onSelectStory]);

  if (!isOpen || !story) return null;

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (currentIndex > 0) {
      onSelectStory(allStories[currentIndex - 1]);
    }
  };

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (currentIndex < allStories.length - 1) {
      onSelectStory(allStories[currentIndex + 1]);
    } else {
      onClose();
    }
  };

  const getStoryIcon = (iconName: string) => {
    switch (iconName) {
      case 'TrendingUp':
        return <TrendingUp className="w-8 h-8 text-emerald-400" />;
      case 'Zap':
        return <Zap className="w-8 h-8 text-emerald-300" />;
      case 'CreditCard':
        return <CreditCard className="w-8 h-8 text-purple-400" />;
      case 'Shield':
        return <Shield className="w-8 h-8 text-blue-400" />;
      default:
        return <Sparkles className="w-8 h-8 text-indigo-400" />;
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xl">
        {/* Modal Backdrop Click to Close */}
        <div className="absolute inset-0" onClick={onClose} />

        {/* Modal Content Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={`relative z-10 w-full max-w-md h-[580px] rounded-3xl p-6 flex flex-col justify-between overflow-hidden shadow-2xl border border-white/20 bg-gradient-to-b ${story.gradient}`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Subtle Ambient Lighting */}
          <div className="absolute -top-24 -right-24 w-60 h-60 bg-white/15 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 w-60 h-60 bg-black/40 rounded-full blur-3xl pointer-events-none" />

          {/* Top Bars: Progress Trackers */}
          <div className="relative z-20 space-y-3">
            <div className="flex gap-1.5 w-full">
              {allStories.map((s, idx) => (
                <div key={s.id} className="h-1 flex-1 bg-white/20 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-white transition-all duration-100 ease-linear rounded-full"
                    style={{
                      width: idx === currentIndex ? `${progress}%` : idx < currentIndex ? '100%' : '0%',
                    }}
                  />
                </div>
              ))}
            </div>

            {/* Header info */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-white/15 backdrop-blur-md flex items-center justify-center border border-white/20">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-white/70 block">
                    {story.tag}
                  </span>
                  <span className="text-sm font-semibold text-white">{story.title}</span>
                </div>
              </div>

              <button
                onClick={onClose}
                className="w-9 h-9 rounded-full bg-black/40 hover:bg-black/60 text-white/80 hover:text-white flex items-center justify-center transition-all border border-white/10"
                aria-label="Close Story"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Center Story Content */}
          <div className="relative z-20 my-auto space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20 shadow-lg">
              {getStoryIcon(story.icon)}
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-black text-white tracking-tight leading-snug">
                {story.content.headline}
              </h2>
              <p className="text-white/80 text-sm leading-relaxed">{story.content.details}</p>
            </div>

            {/* Metric Highlight Box */}
            <div className="bg-black/30 backdrop-blur-md rounded-2xl p-4 border border-white/10">
              <span className="text-xs font-semibold text-white/60 uppercase tracking-wider block">
                {story.content.metricLabel}
              </span>
              <span className="text-3xl font-black text-white font-mono tracking-tight block mt-0.5">
                {story.content.highlightMetric}
              </span>
            </div>

            {/* Bullets */}
            <ul className="space-y-2">
              {story.content.bullets.map((b, i) => (
                <li key={i} className="flex items-center gap-2.5 text-xs text-white/80">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/80" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Bottom Action CTA */}
          <div className="relative z-20 pt-4">
            <button
              onClick={() => {
                if (onActionClick) onActionClick(story.actionType);
                onClose();
              }}
              className="w-full py-3.5 px-6 rounded-2xl bg-white text-slate-950 font-bold text-sm hover:bg-white/90 active:scale-98 transition-all flex items-center justify-center gap-2 shadow-xl"
            >
              <span>{story.actionText}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Left/Right Navigation Touch Areas */}
          <button
            onClick={handlePrev}
            disabled={currentIndex === 0}
            className="absolute left-2 top-1/2 -translate-y-1/2 z-20 p-2 text-white/40 hover:text-white disabled:opacity-0 transition-opacity"
            aria-label="Previous story"
          >
            <ChevronLeft className="w-8 h-8" />
          </button>
          <button
            onClick={handleNext}
            className="absolute right-2 top-1/2 -translate-y-1/2 z-20 p-2 text-white/40 hover:text-white transition-opacity"
            aria-label="Next story"
          >
            <ChevronRight className="w-8 h-8" />
          </button>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
