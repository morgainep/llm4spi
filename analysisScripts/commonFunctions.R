library(data.table)
library(ggplot2)
library(parallel)

############
# ggplot theme

theme_se <- function(){
  theme_minimal(base_line_size = 0) +
    theme(legend.position = 'none',
          #legend.text = element_text(size=10, family = "Arial", color = "gray20"),
          legend.text = element_text(size=6, color = "gray20"),
          legend.background = element_blank(),
          text = element_text(color = "gray20"),
          legend.key.height = unit(0.2, "cm"),
          legend.spacing.x = unit(0.1, 'cm')
          
    ) +
    #theme(text=element_text(size=10, family = "Arial")) +
    theme(text=element_text(size=7)) +
    theme(
      panel.grid.major = element_line(linewidth=0.5, colour = "gray90"),
      panel.grid.minor = element_blank(),
      axis.ticks = element_blank()
    )
}
# Fast list to dataframe transformation
fromListToDF <- function(inputList){
  if (is.null(inputList)){return(NULL)}
  
  #check if some is null and remove
  nullPositions <- which(sapply(inputList,is.null))
  if (length(nullPositions) > 0){
    inputList <- inputList[-nullPositions]    
  }
  
  firstEl <- inputList[[1]][1,]
  
  inputList <- lapply(inputList, function(x){ matrix(unlist(x), ncol=ncol(x))} )
  
  outDF <- as.data.frame(do.call(rbind, inputList),stringsAsFactors=F)
  colnames(outDF) <-names(firstEl)
  
  for(idx in c(1:ncol(outDF))){
    if (class(firstEl[[idx]]) == "logical"){       
      if (is.na(firstEl[[idx]])){
        class(outDF[[idx]]) <- "numeric"
      }else if (outDF[1,idx] == "TRUE" ||outDF[1,idx] == "FALSE"  ){
        outDF[,idx] <- as.logical(outDF[,idx]) * 1      
      }
      class(outDF[[idx]]) <- "numeric"
    }else if (class(firstEl[[idx]]) == "factor"){
      class(firstEl[[idx]]) == "character"
    }else {
      class(outDF[[idx]]) <- class(firstEl[[idx]])
    }
  }
  
  
  return(outDF)
}

# aggregate replica data
aggregate_replicas <- function(tb,
                               id_cols,
                               agg_cols,
                               pass_cols,
                               stats
){
  
  tb$aggregate_replicas_id <- apply(as.matrix(tb[, id_cols]), 1 , paste, collapse = "||")

  summarize <- function(id){
    this_tb <- tb[which(tb$aggregate_replicas_id == id),,drop=FALSE]
    out_tb <- data.frame(row.names = id)
    out_tb[, id_cols] <- this_tb[1,id_cols,drop=FALSE]
    out_tb[, pass_cols] <- this_tb[1,pass_cols,drop=FALSE]
    #st <- stats[1]
    for(st in stats){
      ag <- agg_cols[1]
      for(ag in agg_cols){
        out_tb[,paste0(st," ",ag)] <- get(st)(this_tb[,ag])
      }
    }
    return(out_tb)
  }
  
  summary_table.list <- mclapply(unique(tb$aggregate_replicas_id), summarize ,mc.preschedule = TRUE, mc.cores = n_cores)
  summary.table <- fromListToDF(summary_table.list)
  return(summary.table)
}




# perform pairwise Wilcox test and Vargha Delaney
pairwise_performance_comparison <- function(all_data, uid_cols , test_column, compare_columns, pass_columns, minGruopSize = 5){
  
  if (length(uid_cols) == 1 ){
    all_data$uid <- all_data[ , uid_cols ] 
  }else{
    all_data$uid <- apply( all_data[ , uid_cols ] , 1 , paste , collapse = "|" )
  }
  unique_groups <- unique(all_data$uid)  

    compare_group <- function(group_id, all_data, test_column, compare_columns, pass_columns){
    #cat(group_id,"\n")
    this_data <- all_data[which(all_data$uid == group_id),]
    
    if (length(unique(this_data[,test_column])) != minGruopSize){
      cat(group_id,"\n")
      warning(group_id)
      return(NULL)
    }
    out_data <- as.data.frame(t(combn(unique(this_data[,test_column]), 2)))
    colnames(out_data) <- c("group1","group2")
    i<-1
    for(i in seq(1,nrow(out_data),1)){
      cc <- compare_columns[2]
      for(cc in compare_columns){
        
        val_x <- this_data[which(this_data[,test_column] == out_data$group1[i]), cc]
        val_y <- this_data[which(this_data[,test_column] == out_data$group2[i]), cc]
        median_x <- median(val_x)
        median_y <- median(val_y)
        
        wil_p <- wilcox.test(x = val_x, y = val_y, exact = FALSE)
        vd_p <- VD.A( val_x, val_y)
        
        out_data[i, paste0(cc,"_p")] <- wil_p$p.value
        out_data[i, paste0(cc,"_vde")] <- vd_p$estimate
        out_data[i, paste0(cc,"_vdm")] <- as.character(vd_p$magnitude)
        out_data[i, paste0(cc,"_median_group1")] <- median_x
        out_data[i, paste0(cc,"_median_group2")] <- median_y
        
      }
      
    }
    
    out_data <- cbind(out_data, this_data[1:nrow(out_data),pass_columns,drop=F])
    

    return(out_data)
  }
  
  all_stats.list <-  mclapply(unique_groups, compare_group, 
                              all_data = all_data, test_column = test_column, compare_columns = compare_columns, pass_columns = pass_columns,
                              mc.cores = n_cores)

    all_stats <- fromListToDF(all_stats.list)
  return(all_stats)       
}