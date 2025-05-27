# set current folder and load packages and functions
current_folder <- dirname(rstudioapi::getSourceEditorContext()$path)
setwd(current_folder)
#setwd("../")
getwd()

# load common functions
source("commonFunctions.R")

options(scipen=9999)

# libs
library(jsonlite)
library(data.table)
library(ggplot2)
library(VeryLargeIntegers)

###############################################################################
#
# Functions
#
###############################################################################

getModelName <- function(jsonFile) {
  file_name <- basename(jsonFile)
  model_name <- strsplit(file_name, "_")[[1]][2]
  model_name <- gsub(".gguf", "", model_name)
  return(model_name)
}

#cond_data <- task_data$post_condition[[1]]
processCondition <- function(cond_data) {
  #rep_id <- 1
  out_data <- data.frame()
  for (rep_id in seq(1,length(cond_data),1)) {
    rep_data  <- cond_data[[rep_id]]
    rep_data <- cbind(replica=rep(rep_id, nrow(rep_data)),rep_data)    
    out_data <- rbind(out_data, rep_data)    
    
  }      
  return(out_data)
}

#jsonFile <- res_files[1]
loadJson <- function(jsonFile) {
  
  # get model name
  model_name <- getModelName(jsonFile)
  cat(model_name,"\n")
  # read json
  sample_data <- fromJSON(jsonFile, flatten = T)#[1,3][[1]][[1]]
  
  # list of tasks
  tasks_list <- sample_data[, 1]
  rownames(sample_data) <- tasks_list
  
  # main output table
  out_data <- data.frame()
  
  # process task by task
  task_name <- tasks_list[4]
  for (task_name in tasks_list) {
    task_data <- sample_data[task_name, ]
    # process pre conditions
    if (! is.null(task_data$pre_condition[[1]])) {
      pre_data <- processCondition(task_data$pre_condition[[1]])
      pre_data <- cbind(task = rep(task_name, nrow(pre_data)), model = rep(model_name, nrow(pre_data)), cond = rep("pre", nrow(pre_data)), pre_data )
      out_data <- rbind(out_data, pre_data)
    }
    # process post conditions
    if (! is.null(task_data$post_condition[[1]])) {
      post_data <- processCondition(task_data$post_condition[[1]])
      if (!is.logical(post_data$expected)){
        cat(model_name," ",task_name,"\n")
      }
        
      post_data <- cbind(task = rep(task_name, nrow(post_data)), model = rep(model_name, nrow(post_data)), cond = rep("post", nrow(post_data)), post_data )
      out_data <- rbind(out_data, post_data)
    }
  }
  
  return(out_data)
}

#tb <- summary_table
#replicaId <- summary_table$replica_uid[431345]
analyze_replica <- function(replicaId, tb){
  this_tb <- tb[which(tb$replica_uid == replicaId),]    
  # no data (i.e., no precondition for the task)
  if (nrow(this_tb) == 0){
    next
  }
  # check duplicated tests
  if (nrow(this_tb) != length(unique(this_tb$test))){
    #dup_tests <- rbind(dup_tests,this_tb[which(this_tb$test %in% this_tb$test[which(duplicated(this_tb$test))]),])
    this_tb <- this_tb[which(!duplicated(this_tb$test)),]
  }
  
  colnames(this_tb)
  pass_cols <- c("task", "model", "cond","replica","prog_cc", "solution_cc", "solution_human_comp","Short name", "EvalPlus Leaderboard position","Parameters (B)", "Size (GB)", "Licence")
  this_out <- this_tb[1,pass_cols, drop=F]
  
  # check all replicas has the same number of tests
  this_out$n_tests <- nrow(this_tb)

  this_out$n_TP <- length(which(this_tb$class == "TP"))
  this_out$n_TN <- length(which(this_tb$class == "TN"))
  this_out$n_FP <- length(which(this_tb$class == "FP"))                          
  this_out$n_FN <- length(which(this_tb$class == "FN"))  
  this_out$n_Error <- length(which(this_tb$class == "Error"))  
  this_out$n_Pass <- length(which(this_tb$outcome == "Pass"))
  this_out$n_Fail <- length(which(this_tb$outcome == "Fail"))
  
  #unique(this_tb$suite)
  this_tb_manual <- this_tb[which(this_tb$suite %in% c("human-positive","human-validation")),]

  this_out$n_tests_manual <- nrow(this_tb_manual)
  this_out$n_TP_manual <- length(which(this_tb_manual$class == "TP"))
  this_out$n_TN_manual <- length(which(this_tb_manual$class == "TN"))
  this_out$n_FP_manual  <- length(which(this_tb_manual$class == "FP"))                          
  this_out$n_FN_manual  <- length(which(this_tb_manual$class == "FN"))  
  this_out$n_Error_manual  <- length(which(this_tb_manual$class == "Error"))  
  this_out$n_Pass_manual  <- length(which(this_tb_manual$outcome == "Pass"))
  this_out$n_Fail_manual  <- length(which(this_tb_manual$outcome == "Fail"))
  
  
  this_tb_auto <- this_tb[which(this_tb$suite %in% c("pynguin_negative","pynguin_positive")),]
  
  this_out$n_tests_auto <- nrow(this_tb_auto)
  this_out$n_TP_auto <- length(which(this_tb_auto$class == "TP"))
  this_out$n_TN_auto <- length(which(this_tb_auto$class == "TN"))
  this_out$n_FP_auto  <- length(which(this_tb_auto$class == "FP"))                          
  this_out$n_FN_auto  <- length(which(this_tb_auto$class == "FN"))  
  this_out$n_Error_auto  <- length(which(this_tb_auto$class == "Error"))  
  this_out$n_Pass_auto  <- length(which(this_tb_auto$outcome == "Pass"))
  this_out$n_Fail_auto  <- length(which(this_tb_auto$outcome == "Fail"))

  
  return(this_out)
}

#tb <- task_table
#taskId <-  task_table$uid[344] 
#taskId <-  "HE101 athene-v2-chat post"
analyze_task <- function(taskId, tb){
  cat(taskId,"\n")
  this_tb <- tb[which(tb$uid == taskId),,drop=FALSE]
  # internal check
  if (length(unique(this_tb$n_tests)) != 1 || nrow(this_tb) != 10){
    cat("Check ",taskId)
  }
  # pass cols
  # "task", "model", "cond", "replica", "prog_cc", "solution_cc", "solution_human_comp", "Short name", "EvalPlus Leaderboard position", "Parameters (B)", "Size (GB)", "Licence", 
  # "n_tests", "n_TP", "n_TN", "n_FP", "n_FN", "n_Error", "n_Pass", "n_Fail", "p_Pass", "p_Fail", "p_TP", "p_TN", "p_FP", "p_FN", "p_Error", "uid"
  pass_columns <- c("task", "model", "cond", "prog_cc", "solution_cc", "solution_human_comp", "Short name", "EvalPlus Leaderboard position", "Parameters (B)", "Size (GB)", "Licence","n_tests")
  
  this_out <- this_tb[1,pass_columns, drop=F]  
  
  # compute eval@k
  n_attempts <- nrow(this_tb)
  n_valid <- length(which(this_tb$p_Pass >= 1))
  # evalAt1bis =  if (n_attempts - n_valid > 0){
  #   1 - (as.integer(binom(n_attempts - n_valid, 1)) / as.integer(binom(n_attempts,1)))
  # }else if (n_attempts - n_valid == 0 ){
  #   1
  # }else{
  #   0
  # }
    

  evalAt1 = 1 - (n_attempts - n_valid)/(n_attempts)
  
  this_out$evalAt1 = evalAt1
  # this_out$evalAt1bis = as.numeric(evalAt1bis)
  
  this_out$n_valid <- length(which(this_tb$n_Fail == 0))
  this_out$p_valid <- this_out$n_valid / nrow(this_tb)
  
  this_out$avg_p_TP <- mean(this_tb$p_TP)
  this_out$sd_p_TP <- sd(this_tb$p_TP)
  
  this_out$avg_p_TN <- mean(this_tb$p_TN)
  this_out$sd_p_TN <- sd(this_tb$p_TN)
  
  this_out$avg_p_FP <- mean(this_tb$p_FP)
  this_out$sd_p_FP <- sd(this_tb$p_FP)
  
  this_out$avg_p_FN <- mean(this_tb$p_FN)
  this_out$sd_p_FN <- sd(this_tb$p_FN)
  
  this_out$avg_p_Error <- mean(this_tb$p_Error)
  this_out$sd_p_Error <- sd(this_tb$p_Error)
  
  this_out$avg_p_Pass <- mean(this_tb$p_Pass)
  this_out$sd_p_Pass <- sd(this_tb$p_Pass)
  
  this_out$avg_p_Fail <- mean(this_tb$p_Fail)
  this_out$sd_p_Fail <- sd(this_tb$p_Fail)
  
  
  this_out$n_valid_manual <- length(which(this_tb$n_Fail_manual == 0))
  this_out$p_valid_manual <- this_out$n_valid_manual / nrow(this_tb)
  this_out$avg_p_Pass_manual <- mean(this_tb$p_Pass_manual)
  
  this_out$n_valid_auto <- length(which(this_tb$n_Fail_auto == 0))
  this_out$p_valid_auto <- this_out$n_valid_auto / nrow(this_tb)
  this_out$avg_p_Pass_auto <- mean(this_tb$p_Pass_auto)
  
  this_out$n_replica 
  this_out$n_at_least_one_error <- length(which(this_tb$n_Error > 0))
  this_out$n_all_error <- length(which(this_tb$n_Error == this_tb$n_tests))  
  
  return(this_out)
}

#tb <- model_table
#modelId <- model_table$uid[34]
analyze_model <- function(modelId, tb){
  this_tb <- tb[which(tb$uid == modelId ),]  
  pass_columns <- c("model", "cond", "Short name", "EvalPlus Leaderboard position", "Parameters (B)", "Size (GB)", "Licence")
  
  this_tb$n_misclassified <- this_tb$n_valid_manual - this_tb$n_valid
  
  
  this_out <- this_tb[1,pass_columns, drop=F]  
  
  this_out$avg_evalAt1 <- mean(this_tb$evalAt1)
  this_out$sd_evalAt1 <- sd(this_tb$evalAt1)
  this_out$avg_Pass <- mean(this_tb$avg_p_Pass)
  this_out$sd_Pass <- sd(this_tb$avg_p_Pass)
  this_out$min_Pass <- min(this_tb$avg_p_Pass)
  this_out$max_Pass <- max(this_tb$avg_p_Pass)
  this_out$avg_Error <- mean(this_tb$avg_p_Error)
  this_out$sd_Error <- sd(this_tb$avg_p_Error)
  
  this_out$avg_Valid <- mean(this_tb$p_valid)
  this_out$sd_Valid <- sd(this_tb$p_valid)
  this_out$avg_Misclassified <- mean(this_tb$n_misclassified)
  this_out$sd_Misclassified <- sd(this_tb$n_misclassified)
  this_out$tot_Misclassified <- sum(this_tb$n_misclassified)
  this_out$tot_Valid <- sum(this_tb$n_valid)
  this_out$tot_ManualValid <- sum(this_tb$n_valid_manual)
  
  return(this_out)
}


###############################################################################
#
# Computation
#
###############################################################################

# out files
summary_table_file <- "tables/summary_table.tsv"
task_table_file <- "tables/task_table.tsv"
model_table_file <- "tables/model_table.tsv"
benchmark_table_file <- "tables/benchmark_table.tsv"

# load data
post_mortem_folder = "rawData"
res_files = list.files(path = post_mortem_folder, pattern = "extendedtestResults", full.names = T)

data_set_file = "tables/HEx-compact.json"
data_set <-fromJSON(data_set_file)

models_description_file = "tables/model_list.csv"
models_description <- fread(models_description_file, data.table = F)

########################
# load the json files
summary_table <- data.frame()
#rs <- res_files[1]
for (rs in res_files) {
  rs_data <- loadJson(rs)
  summary_table <- rbind(summary_table,rs_data)
}

#unique(summary_table$result)
#summary_table[which(summary_table$result == '612345123456'),]
#null_tb <- summary_table[which(is.na(summary_table$result)),]


######################
# add information about models
before_merge <- nrow(summary_table)
summary_table <- merge(summary_table, models_description, by.x = 'model', by.y = 'Full name')
if (nrow(summary_table) != before_merge){
  stop()
}

######################
# classify test outcomes 

summary_table$raw_result <- as.character(summary_table$result)


# NOTE: sometimes expected is 1/0 and not TRUE/FALSE
#summary_table$expected <- sapply(summary_table$expected, function(x){if (x==1) TRUE else FALSE})
# NOTE: some results are not basic types and need to be handled
#summary_table <- summary_table[which(sapply(summary_table$result, function(X){length(X)}) == 1),]
#not_primary_type <- summary_table[which(sapply(summary_table$result, function(X){length(X)}) != 1),] 
summary_table$result[which(sapply(summary_table$result, function(X){length(X)}) != 1)] <- "not primary"

# setdiff(which(summary_table$expected == "TRUE"),which(summary_table$expected == TRUE))
# setdiff(which(summary_table$expected == TRUE),which(summary_table$expected == "TRUE"))
# setdiff(which(summary_table$expected == "FALSE"),which(summary_table$expected == FALSE))
# setdiff(which(summary_table$expected == FALSE),which(summary_table$expected == "FALSE"))

# classify response
summary_table$class <- NA
summary_table$class[which(summary_table$result == TRUE & summary_table$expected == TRUE)] <- "TP"
summary_table$class[which(summary_table$result == TRUE & summary_table$expected == FALSE)] <- "FP"
summary_table$class[which(summary_table$result == FALSE & summary_table$expected == FALSE)] <- "TN"
summary_table$class[which(summary_table$result == FALSE & summary_table$expected == TRUE)] <- "FN"
summary_table$class[which(is.na(summary_table$class))]  <- "Error"

# only pass or fail
summary_table$outcome <- NA
summary_table$outcome[which(summary_table$class %in% c("TP","TN"))] <- "Pass"
summary_table$outcome[which(summary_table$class %in% c("FP","FN","Error"))] <- "Fail"

# type of test generation
summary_table$test_generator <- NA
summary_table$test_generator[grep("human",summary_table$suite)] <- "Manual"
summary_table$test_generator[grep("pyn",summary_table$suite)] <- "Auto"

summary_table$test_type <- NA
summary_table$test_type[summary_table$expected] <- "Positive"
summary_table$test_type[!summary_table$expected] <- "Negative"

##############################
# add info from data set such as CC
summary_table$prog_cc <- NA
summary_table$solution_cc <- NA
summary_table$solution_human_comp <- NA

#i <- 1
for(i in seq(1,nrow(data_set),1)){
  this_ds <- data_set[i,,drop=F]  
  this_summary_ids <- which(summary_table$task == this_ds$task_id)
  summary_table$prog_cc[this_summary_ids]  <- this_ds$prg_CC
  
  this_summary_ids_post <- which(summary_table$task == this_ds$task_id & summary_table$cond == "post")
  summary_table$solution_cc[this_summary_ids_post] <- this_ds$post_condition_CC
  summary_table$solution_human_comp[this_summary_ids_post] <- this_ds$post_condition_complexity
  
  this_summary_ids_pre <- which(summary_table$task == this_ds$task_id & summary_table$cond == "pre")
  summary_table$solution_cc[this_summary_ids_pre] <- this_ds$pre_condition_CC
  summary_table$solution_human_comp[this_summary_ids_pre] <- this_ds$pre_condition_complexity
}

fwrite(summary_table, summary_table_file, quote = F, sep = "\t", row.names = F, col.names = T)


#####################
# aggregate test data: for each replica summarize number of pass, fail, tp ...

colnames(summary_table)
# "model", "task", "cond", "replica", "suite", "test", "result", "expected", "Short name", "EvalPlus Leaderboard position", "Link", 
# "Parameters (B)", "Size (GB)", "post (HE)", "pre (HE)", "Licence", "class", "outcome", "test_generator", "test_type", "prog_cc", "solution_cc", "solution_human_comp"

summary_table$replica_uid <- paste(summary_table$model, summary_table$task, summary_table$cond, summary_table$replica)

task_table.list <- mclapply(unique(summary_table$replica_uid), FUN = analyze_replica, tb = summary_table, mc.preschedule = T, mc.cores = 8)
task_table <- fromListToDF(task_table.list)

task_table$p_Pass <- task_table$n_Pass / task_table$n_tests
task_table$p_Fail <- task_table$n_Fail / task_table$n_tests
task_table$p_TP <- task_table$n_TP / task_table$n_tests
task_table$p_TN <- task_table$n_TN / task_table$n_tests
task_table$p_FP <- task_table$n_FP / task_table$n_tests
task_table$p_FN <- task_table$n_FN / task_table$n_tests
task_table$p_Error <- task_table$n_Error / task_table$n_tests

task_table$p_Pass_manual <- task_table$n_Pass_manual / task_table$n_tests_manual
task_table$p_Fail_manual <- task_table$n_Fail_manual / task_table$n_tests_manual
task_table$p_TP_manual <- task_table$n_TP_manual / task_table$n_tests_manual
task_table$p_TN_manual <- task_table$n_TN_manual / task_table$n_tests_manual
task_table$p_FP_manual <- task_table$n_FP_manual / task_table$n_tests_manual
task_table$p_FN_manual <- task_table$n_FN_manual / task_table$n_tests_manual
task_table$p_Error_manual <- task_table$n_Error_manual / task_table$n_tests_manual

task_table$p_Pass_auto <- task_table$n_Pass_auto / task_table$n_tests_auto
task_table$p_Fail_auto <- task_table$n_Fail_auto / task_table$n_tests_auto
task_table$p_TP_auto <- task_table$n_TP_auto / task_table$n_tests_auto
task_table$p_TN_auto <- task_table$n_TN_auto / task_table$n_tests_auto
task_table$p_FP_auto <- task_table$n_FP_auto / task_table$n_tests_auto
task_table$p_FN_auto <- task_table$n_FN_auto / task_table$n_tests_auto
task_table$p_Error_auto <- task_table$n_Error_auto / task_table$n_tests_auto

fwrite(task_table, task_table_file, quote = F, sep = "\t", row.names = F, col.names = T)

###################
# aggregate replicas: for each task get mean pass, mean prop, eval@1


task_table$uid <- paste(task_table$task, task_table$model, task_table$cond)
model_table.list <- mclapply(unique(task_table$uid), FUN = analyze_task, tb = task_table, mc.preschedule = F, mc.cores = 8)
model_table <- fromListToDF(model_table.list)
#aa<-model_table[which(model_table$evalAt1 != model_table$evalAt1bis),]
#lapply(unique(task_table$uid), FUN = analyze_task, tb = task_table)

fwrite(model_table, model_table_file, quote = F, sep = "\t", row.names = F, col.names = T)

###################
# aggregate tasks: a row for each model

model_table$uid <- paste(model_table$model,model_table$cond)

benchmark_table.list <- mclapply(unique(model_table$uid), FUN = analyze_model, tb = model_table, mc.preschedule = F, mc.cores = 8)
benchmark_table <- fromListToDF(benchmark_table.list)

fwrite(benchmark_table, file = benchmark_table_file, quote = F, sep = "\t", row.names = F, col.names = T)

#############################################
#
# Inspect data: to remove
#
#############################################
# colnames(benchmark_table)
# 
# ggplot(benchmark_table, aes(x=`Short name`, y=avg_Pass, fill = Licence)) +
#   geom_bar(stat = 'identity')+
#   geom_errorbar(aes(ymin=pmax(0,avg_Pass-sd_Pass), ymax=avg_Pass+sd_Pass), width=.2,position=position_dodge(.9)) +
#   geom_point(aes(y=avg_evalAt1)) +
#   facet_wrap(~cond) +
#   theme(axis.text.x = element_text(angle = 90, hjust = 1))
# 
# 
# 
# # inspect data
# ggplot(model_table, aes(x=`Short name`, y=evalAt1, colour = Licence)) +
#   geom_boxplot() +
#   facet_wrap(~cond) +
#   theme(axis.text.x = element_text(angle = 90, hjust = 1))
# 
# 
# colnames(task_table)
# ggplot(task_table, aes(x=`Short name`, y=p_Pass, colour = Licence)) +
#   geom_boxplot() +
#   facet_wrap(task~cond, scales = 'free_x') +
#   theme(axis.text.x = element_text(angle = 90, hjust = 1))
# 
# ggplot(task_table, aes(x=`Short name`, y=p_FP, colour = Licence)) +
#   geom_boxplot() +
#   facet_wrap(task~cond, scales = 'free_x') +
#   theme(axis.text.x = element_text(angle = 90, hjust = 1))
# 
# 
# checkTask <- c("HE108")
# checkCond <- "post"
# checkModel <- c("Athene", "GTP3.5", "Haiku")
# 
# checkTB <- task_table[which(task_table$`Short name` %in% checkModel & task_table$cond == checkCond & task_table$task %in% checkTask),]
# 
# 
# ggplot(task_table, aes(x=model, y=p_Pass)) +
#   geom_bar(stat = "mean" ) +
#   theme(axis.text.x = element_text(angle = 90, hjust = 1))
# 
# 
# 
# 
# 
# 
# 
# # inspect data
# fail_table <- summary_table[which(summary_table$class == "Fail"),]
# not_fail_table <- summary_table[which(summary_table$class != "Fail"),]
# sort(table(fail_table$model))
# sort(table(fail_table$task))
# checkModel <-"claude-3-7-sonnet-20250219" 
# checkTask <- "HE141"
# specific_task <- summary_table[which(summary_table$task == checkTask & summary_table$model == checkModel ),]
# table(specific_task$class)
# 
# #specific_test <- summary_table[which(summary_table$task == "HE1" & summary_table$cond == "pre" & summary_table$test == "['()']"),]
# 
# #prop_table <- prop.table(table(summary_table[which(summary_table$class != "Fail"),c("class","model")] ),2)
# 
# prop_table <- table(not_fail_table[,c("class","model")] )
# prop_table <- prop.table(table(not_fail_table[,c("class","model")] ),2)
# prop_table <- prop.table(table(summary_table[,c("class","model")] ),2)
# 
# tmp = as.data.frame(t(prop_table))
# sort_model <- tmp$model[which(tmp$class == "Fail")][order(tmp$Freq[which(tmp$class == "Fail")])]
# sort_model <- tmp$model[which(tmp$class == "TP")][order(tmp$Freq[which(tmp$class == "TP")], decreasing = T)]
# tmp$Model = factor(tmp$model, levels = sort_model)
# 
# ggplot(tmp, aes(x=Model, y=Freq)) +
#          geom_bar(stat = "identity" ) + 
#         facet_wrap(~class) +
#         theme(axis.text.x = element_text(angle = 90, hjust = 1))
# 
# colnames(summary_table)
# ggplot(summary_table, aes())
# 
# 
# ## check
# 
# testTB <-  task_table[which(task_table$`Short name` == "Athene" & task_table$task == "HE1" & task_table$cond == "post"),]
# 
