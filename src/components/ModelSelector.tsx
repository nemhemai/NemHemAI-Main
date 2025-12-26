import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

export const models = [
  { id: 'mistral:latest', name: 'Mistral', description: 'General / Fast', category: 'General', color: 'from-blue-500 to-cyan-600' },
  { id: 'llama3.1:latest', name: 'Llama 3.1', description: 'General / Reasoning', category: 'General', color: 'from-blue-500 to-cyan-600' },
  // { id: 'deepseek-v2:latest', name: 'DeepSeek V2', description: 'Coding + Reasoning', category: 'Coding', color: 'from-green-500 to-emerald-600' },
  { id: 'qwen2.5vl:latest', name: 'Qwen 2.5 VL', description: 'Multimodal (Text + Image)', category: 'Multimodal', color: 'from-purple-500 to-pink-600' },
  { id: 'deepseek-coder-v2:latest', name: 'DeepSeek Coder V2', description: 'Advanced Coding', category: 'Coding', color: 'from-green-500 to-emerald-600' },
];

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
  disabled?: boolean;
}

export const ModelSelector = ({ selectedModel, onModelChange, disabled }: ModelSelectorProps) => {
  const currentModel = models.find(model => model.id === selectedModel);

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-slate-400 font-medium">Model:</span>
      <Select value={selectedModel} onValueChange={onModelChange} disabled={disabled}>
        <SelectTrigger className="w-[220px] bg-slate-900 border-[#A259FF] text-white hover:bg-[#6C47FF]/10 transition-all duration-200 shadow-lg rounded-xl">
          <SelectValue>
            <div className="flex items-center gap-3">
              <Badge 
                variant="outline" 
                className={`text-xs bg-gradient-to-r from-[#6C47FF] to-[#A259FF] text-white border-0`}
              >
                {currentModel?.category}
              </Badge>
              <span className="font-medium">{currentModel?.name}</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="bg-slate-900 border-[#A259FF] shadow-2xl rounded-xl max-h-[500px] overflow-y-auto">
          {models.map((model) => (
            <SelectItem 
              key={model.id} 
              value={model.id}
              className="text-white hover:bg-[#6C47FF]/20 focus:bg-[#A259FF]/20 cursor-pointer rounded-xl"
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                  <Badge 
                    variant="outline" 
                    className={`text-xs bg-gradient-to-r from-[#6C47FF] to-[#A259FF] text-white border-0`}
                  >
                    {model.category}
                  </Badge>
                  <span className="font-medium">{model.name}</span>
                </div>
                <span className="text-xs text-slate-400 ml-3">{model.description}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};
