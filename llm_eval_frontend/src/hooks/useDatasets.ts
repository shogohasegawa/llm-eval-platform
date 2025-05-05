import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetsApi } from "../api/datasets";
import { Dataset, DatasetUploadType } from "../types/dataset";

/**
 * データセット関連のカスタムフック
 */

// データセット一覧を取得するフック
export const useDatasets = (type) => {
  return useQuery({
    queryKey: ["datasets", type],
    queryFn: () => datasetsApi.getDatasets(type)
  });
};

// 特定のデータセットを取得するフック（名前ベース）
export const useDatasetByName = (name) => {
  return useQuery({
    queryKey: ["datasets", "detail", name],
    queryFn: () => datasetsApi.getDatasetByName(name),
    enabled: name ? true : false
  });
};

// データセットを削除するフック
export const useDeleteDataset = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (filePath) => datasetsApi.deleteDataset(filePath),
    onSuccess: () => {
      // 成功時にデータセット一覧を再取得
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
    }
  });
};

// JSONファイルをアップロードするフック
export const useUploadJsonFile = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, type }) => datasetsApi.uploadJsonFile(file, type),
    onSuccess: () => {
      // 成功時にデータセット一覧を再取得
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
    }
  });
};
