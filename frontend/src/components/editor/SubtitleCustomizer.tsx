'use client';

import React, { useState } from 'react';
import { SubtitleStyleConfig } from '@/types';
import { Type, Palette, Sparkles, Check, Loader2 } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { getBackendUrl } from '@/lib/utils';

interface SubtitleCustomizerProps {
  clipId: string;
  initialStyle?: SubtitleStyleConfig;
  onStyleUpdated: (updated: SubtitleStyleConfig) => void;
}

const DEFAULT_STYLE: SubtitleStyleConfig = {
  font_family: 'Montserrat',
  font_size: 28,
  primary_color: '#FFFFFF',
  highlight_color: '#FFD700',
  outline_color: '#000000',
  outline_width: 3,
  position: 'middle-bottom',
  karaoke_effect: true,
};

const COLOR_PRESETS = ['#FFFFFF', '#FFD700', '#00FFFF', '#FF0055', '#39FF14', '#FFA500'];

export const SubtitleCustomizer: React.FC<SubtitleCustomizerProps> = ({
  clipId,
  initialStyle,
  onStyleUpdated,
}) => {
  const [style, setStyle] = useState<SubtitleStyleConfig>({
    ...DEFAULT_STYLE,
    ...(initialStyle || {}),
  });
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setSavedSuccess(false);
    setErrorMsg(null);

    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) {
        setErrorMsg('Please sign in to save subtitle styling.');
        setSaving(false);
        return;
      }

      const backendUrl = getBackendUrl();
      const res = await fetch(`${backendUrl}/api/v1/clips/${clipId}/subtitles`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ subtitle_style: style }),
      });

      if (res.ok) {
        setSavedSuccess(true);
        onStyleUpdated(style);
        setTimeout(() => setSavedSuccess(false), 3000);
      } else {
        const errData = await res.json().catch(() => ({}));
        setErrorMsg(errData.detail || 'Failed to save subtitle style.');
      }
    } catch (err: any) {
      console.error('Failed to update subtitle styling:', err);
      setErrorMsg(err.message || 'Network error while saving.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-3xl border border-surfaceBorder bg-surface p-6 shadow-xl">
      <div className="flex items-center gap-2 mb-4 text-xs font-semibold text-brand-400 uppercase tracking-wider">
        <Sparkles className="h-4 w-4" /> Styled Karaoke Subtitles
      </div>

      <div className="space-y-5 text-sm">
        {/* Font Family */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5 flex items-center gap-1.5">
            <Type className="h-3.5 w-3.5" /> Font Typeface
          </label>
          <select
            value={style.font_family}
            onChange={(e) => setStyle({ ...style, font_family: e.target.value })}
            className="w-full rounded-xl border border-surfaceBorder bg-background px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
          >
            <option value="Montserrat">Montserrat ExtraBold (Default)</option>
            <option value="Impact">Impact (Bold Meme Style)</option>
            <option value="Roboto">Roboto Condensed</option>
            <option value="Inter">Inter UI Modern</option>
          </select>
        </div>

        {/* Highlight Color (Karaoke Word Color) */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5 flex items-center gap-1.5">
            <Palette className="h-3.5 w-3.5" /> Karaoke Word Highlight Color
          </label>
          <div className="flex items-center gap-2">
            {COLOR_PRESETS.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setStyle({ ...style, highlight_color: color })}
                className={`h-7 w-7 rounded-full border-2 transition-all ${
                  style.highlight_color.toLowerCase() === color.toLowerCase()
                    ? 'border-white scale-110 shadow-lg'
                    : 'border-transparent'
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>

        {/* Primary Color */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">
            Base Spoken Text Color
          </label>
          <div className="flex items-center gap-2">
            {['#FFFFFF', '#E0E0E0', '#FFD700', '#00FFFF'].map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setStyle({ ...style, primary_color: color })}
                className={`h-7 w-7 rounded-full border-2 transition-all ${
                  style.primary_color.toLowerCase() === color.toLowerCase()
                    ? 'border-brand-400 scale-110'
                    : 'border-transparent'
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>

        {/* Outline Width */}
        <div>
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Text Outline Thickness</span>
            <span className="font-bold text-white">{style.outline_width}px</span>
          </div>
          <input
            type="range"
            min={1}
            max={6}
            value={style.outline_width}
            onChange={(e) => setStyle({ ...style, outline_width: Number(e.target.value) })}
            className="w-full accent-brand-500"
          />
        </div>

        {/* Karaoke Effect Switch */}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs font-medium text-gray-300">
            Word-by-Word Karaoke Animation
          </span>
          <input
            type="checkbox"
            checked={style.karaoke_effect}
            onChange={(e) => setStyle({ ...style, karaoke_effect: e.target.checked })}
            className="h-4 w-4 rounded accent-brand-500"
          />
        </div>

        {errorMsg && (
          <p className="text-xs text-rose-400">{errorMsg}</p>
        )}

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-brand-600 py-3 text-xs font-bold text-white shadow-lg hover:bg-brand-500 transition-all disabled:opacity-50"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Saving Style...
            </>
          ) : savedSuccess ? (
            <>
              <Check className="h-4 w-4 text-emerald-300" /> Saved Successfully!
            </>
          ) : (
            'Apply & Save Subtitle Style'
          )}
        </button>
      </div>
    </div>
  );
};
