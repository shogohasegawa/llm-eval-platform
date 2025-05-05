import { v4 as uuidv4 } from 'uuid';
import { providersRepository } from './providers.repository';
import { datasetsRepository } from './datasets.repository';
import { inferencesRepository } from './inferences.repository';
import { metricsRepository } from './metrics.repository';
import { ModelFormData } from '../types/provider';

/**
 * アプリケーションの初期データを設定するクラス
 */
class DatabaseSetup {
  /**
   * 初期データの設定を実行
   */
  async setupInitialData() {
    console.log('Setting up initial data...');
    
    // プロバイダを作成
    const openaiProvider = this.createOpenAIProvider();
    const azureProvider = this.createAzureProvider();
    const ollamaProvider = this.createOllamaProvider();
    
    // モデルを作成
    this.createOpenAIModels(openaiProvider.id);
    this.createAzureModels(azureProvider.id);
    this.createOllamaModels(ollamaProvider.id);
    
    // データセットを作成
    const qaDataset = this.createQADataset();
    const summaryDataset = this.createSummaryDataset();
    
    // メトリクスを作成
    this.createMetrics();
    
    // 推論を作成
    this.createSampleInference(openaiProvider.id, qaDataset.id);
    
    console.log('Initial data setup completed');
  }
  
  // OpenAIプロバイダの作成
  createOpenAIProvider() {
    try {
      const provider = providersRepository.createProvider({
        name: 'OpenAI',
        type: 'openai',
        endpoint: 'https://api.openai.com/v1',
        apiKey: 'sk-sample-key-openai',
        isActive: true
      });
      console.log(`Created OpenAI provider: ${provider.id}`);
      return provider;
    } catch (error) {
      console.error('Failed to create OpenAI provider:', error);
      throw error;
    }
  }
  
  // Azureプロバイダの作成
  createAzureProvider() {
    try {
      const provider = providersRepository.createProvider({
        name: 'Azure OpenAI',
        type: 'azure',
        endpoint: 'https://example-azure-openai.openai.azure.com',
        apiKey: 'azure-sample-key',
        isActive: true
      });
      console.log(`Created Azure provider: ${provider.id}`);
      return provider;
    } catch (error) {
      console.error('Failed to create Azure provider:', error);
      throw error;
    }
  }
  
  // Ollamaプロバイダの作成
  createOllamaProvider() {
    try {
      const provider = providersRepository.createProvider({
        name: 'Ollama',
        type: 'ollama',
        endpoint: 'http://localhost:11434/api/generate',
        apiKey: '',
        isActive: true
      });
      console.log(`Created Ollama provider: ${provider.id}`);
      return provider;
    } catch (error) {
      console.error('Failed to create Ollama provider:', error);
      throw error;
    }
  }
  
  // OpenAIモデルの作成
  createOpenAIModels(providerId: string) {
    try {
      const gpt4ModelData: ModelFormData = {
        providerId: providerId,
        name: 'gpt-4',
        displayName: 'GPT-4',
        description: 'OpenAI GPT-4 model',
        endpoint: 'https://api.openai.com/v1',
        apiKey: 'sk-sample-key-openai',
        isActive: true
      };
      
      const gpt35TurboModelData: ModelFormData = {
        providerId: providerId,
        name: 'gpt-3.5-turbo',
        displayName: 'GPT-3.5 Turbo',
        description: 'OpenAI GPT-3.5 Turbo model',
        endpoint: 'https://api.openai.com/v1',
        apiKey: 'sk-sample-key-openai',
        isActive: true
      };
      
      const gpt4 = providersRepository.createModel(gpt4ModelData);
      const gpt35Turbo = providersRepository.createModel(gpt35TurboModelData);
      
      console.log(`Created OpenAI models: ${gpt4.id}, ${gpt35Turbo.id}`);
    } catch (error) {
      console.error('Failed to create OpenAI models:', error);
      throw error;
    }
  }
  
  // Azureモデルの作成
  createAzureModels(providerId: string) {
    try {
      const gpt4ModelData: ModelFormData = {
        providerId: providerId,
        name: 'gpt-4',
        displayName: 'Azure GPT-4',
        description: 'Azure-hosted GPT-4 model',
        endpoint: 'https://example-azure-openai.openai.azure.com',
        apiKey: 'azure-sample-key',
        isActive: true
      };
      
      const gpt4 = providersRepository.createModel(gpt4ModelData);
      
      console.log(`Created Azure model: ${gpt4.id}`);
    } catch (error) {
      console.error('Failed to create Azure models:', error);
      throw error;
    }
  }
  
  // Ollamaモデルの作成
  createOllamaModels(providerId: string) {
    try {
      const llama2ModelData: ModelFormData = {
        providerId: providerId,
        name: 'llama2',
        displayName: 'Llama 2',
        description: 'Meta\'s Llama 2 model',
        endpoint: 'http://localhost:11434/api/generate',
        apiKey: '',
        isActive: true
      };
      
      const mistralModelData: ModelFormData = {
        providerId: providerId,
        name: 'mistral',
        displayName: 'Mistral 7B',
        description: 'Mistral 7B model',
        endpoint: 'http://localhost:11434/api/generate',
        apiKey: '',
        isActive: true
      };
      
      const llama2 = providersRepository.createModel(llama2ModelData);
      const mistral = providersRepository.createModel(mistralModelData);
      
      console.log(`Created Ollama models: ${llama2.id}, ${mistral.id}`);
    } catch (error) {
      console.error('Failed to create Ollama models:', error);
      throw error;
    }
  }
  
  // QAデータセットの作成
  createQADataset() {
    try {
      const dataset = datasetsRepository.createDataset({
        name: 'General Knowledge QA',
        description: 'A dataset of general knowledge questions and answers',
        type: 'qa'
      });
      
      // QAアイテムの追加
      const questions = [
        {
          input: 'What is the capital of France?',
          expectedOutput: 'The capital of France is Paris.'
        },
        {
          input: 'Who wrote "Romeo and Juliet"?',
          expectedOutput: 'William Shakespeare wrote "Romeo and Juliet".'
        },
        {
          input: 'What is the chemical symbol for gold?',
          expectedOutput: 'The chemical symbol for gold is Au.'
        },
        {
          input: 'What is the tallest mountain in the world?',
          expectedOutput: 'Mount Everest is the tallest mountain in the world.'
        },
        {
          input: 'Who painted the Mona Lisa?',
          expectedOutput: 'Leonardo da Vinci painted the Mona Lisa.'
        }
      ];
      
      for (const q of questions) {
        datasetsRepository.addDatasetItem(dataset.id, q);
      }
      
      console.log(`Created QA dataset: ${dataset.id} with ${questions.length} items`);
      return dataset;
    } catch (error) {
      console.error('Failed to create QA dataset:', error);
      throw error;
    }
  }
  
  // サマリーデータセットの作成
  createSummaryDataset() {
    try {
      const dataset = datasetsRepository.createDataset({
        name: 'Text Summaries',
        description: 'A dataset for text summarization',
        type: 'summarization'
      });
      
      // サマリーアイテムの追加
      const texts = [
        {
          input: `Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by humans or animals. Leading AI textbooks define the field as the study of "intelligent agents": any system that perceives its environment and takes actions that maximize its chance of achieving its goals. Some popular accounts use the term "artificial intelligence" to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving", however this definition is rejected by major AI researchers.`,
          expectedOutput: 'Artificial intelligence is intelligence demonstrated by machines. It focuses on systems that perceive their environment and act to achieve goals. While some describe AI as machines mimicking human cognitive functions, major researchers reject this definition.'
        },
        {
          input: `The climate of Earth is the result of a balance of factors. The primary source of energy is sunlight, which is absorbed by the Earth's surface and atmosphere. This energy is then radiated back into space as heat. The greenhouse effect is the process by which certain gases in the atmosphere trap some of this outgoing heat, keeping the planet's surface warmer than it would be otherwise. Human activities, particularly the burning of fossil fuels, have increased the concentration of greenhouse gases in the atmosphere, enhancing the greenhouse effect and leading to global warming.`,
          expectedOutput: 'Earth\'s climate results from a balance where sunlight is absorbed and radiated as heat. Greenhouse gases trap some of this heat. Human activities, especially fossil fuel burning, have increased these gases, enhancing the greenhouse effect and causing global warming.'
        }
      ];
      
      for (const t of texts) {
        datasetsRepository.addDatasetItem(dataset.id, t);
      }
      
      console.log(`Created Summary dataset: ${dataset.id} with ${texts.length} items`);
      return dataset;
    } catch (error) {
      console.error('Failed to create Summary dataset:', error);
      throw error;
    }
  }
  
  // メトリクスの作成
  createMetrics() {
    try {
      console.log('Creating default metrics...');
      
      const exactMatch = metricsRepository.createMetric({
        name: 'Exact Match',
        type: 'exact_match',
        description: 'Percentage of responses that exactly match the expected output',
        isHigherBetter: true
      });
      
      const latency = metricsRepository.createMetric({
        name: 'Average Latency',
        type: 'latency',
        description: 'Average response time in milliseconds',
        isHigherBetter: false
      });
      
      const tokenCount = metricsRepository.createMetric({
        name: 'Average Token Count',
        type: 'token_count',
        description: 'Average number of tokens in responses',
        isHigherBetter: false
      });
      
      console.log(`Created metrics: ${exactMatch.id}, ${latency.id}, ${tokenCount.id}`);
    } catch (error) {
      console.error('Failed to create metrics:', error);
      // エラーを投げずに続行できるようにする
      console.log('Continuing setup despite metrics error');
    }
  }
  
  // サンプル推論の作成
  async createSampleInference(providerId: string, datasetId: string) {
    try {
      // プロバイダからモデルを取得
      const models = providersRepository.getProviderModels(providerId);
      if (!models.length) {
        throw new Error(`No models found for provider ${providerId}`);
      }
      
      // 推論を作成
      const inference = inferencesRepository.createInference({
        name: 'Sample QA Run',
        description: 'Sample inference on QA dataset',
        datasetId,
        providerId,
        modelId: models[0].id
      });
      
      // 推論を実行
      await inferencesRepository.runInference(inference.id);
      
      // 完了するまで待機するシミュレーション
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // メトリクスを適用
      const metrics = metricsRepository.calculateAndApplyMetrics(inference.id);
      
      console.log(`Created and ran sample inference: ${inference.id}`);
      console.log(`Applied metrics: ${JSON.stringify(metrics)}`);
    } catch (error) {
      console.error('Failed to create sample inference:', error);
      throw error;
    }
  }
}

// 使用方法
export const databaseSetup = new DatabaseSetup();