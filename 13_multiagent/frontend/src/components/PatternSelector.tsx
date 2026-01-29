import { Pattern } from '../lib/types';

interface PatternSelectorProps {
  patterns: Pattern[];
  selectedPattern: string;
  onSelectPattern: (patternId: string) => void;
}

export default function PatternSelector({
  patterns,
  selectedPattern,
  onSelectPattern,
}: PatternSelectorProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Multi-Agent Pattern</h2>
      <div className="space-y-2">
        {patterns.map((pattern) => (
          <div key={pattern.id} className="flex items-start">
            <input
              type="radio"
              id={pattern.id}
              name="pattern"
              value={pattern.id}
              checked={selectedPattern === pattern.id}
              onChange={(e) => onSelectPattern(e.target.value)}
              className="mt-1 mr-3 text-blue-600"
            />
            <label htmlFor={pattern.id} className="flex-1 cursor-pointer">
              <div className="font-medium text-gray-900">{pattern.name}</div>
              <div className="text-sm text-gray-600">{pattern.description}</div>
              <div className="flex flex-wrap gap-1 mt-1">
                {pattern.concepts.map((concept, idx) => (
                  <span
                    key={idx}
                    className="inline-block px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded"
                  >
                    {concept}
                  </span>
                ))}
              </div>
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
